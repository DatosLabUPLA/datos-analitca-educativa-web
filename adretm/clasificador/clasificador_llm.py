"""
clasificador_llm.py
===================

Clasifica registros (artículos, tesis, proyectos…) con un LLM a partir de un catálogo
cerrado que vive en una hoja de cálculo. Nada de este módulo es específico de ETM:
para otro tema basta con otro catálogo y otro mapeo de campos.

El catálogo son dos tablas (pestañas de Google Sheets o archivos CSV):

catalogo_dimensiones  · una fila por dimensión
    DIMENSION       nombre estable en MAYÚSCULAS (DOMINIO, NIVEL…)
    ORDEN           orden de presentación en el prompt y en la web
    PASADA          1, 2, … (en qué corrida se pregunta). Vacío en los vocabularios.
    CARDINALIDAD    una         → exactamente una clave (o `no_determinable`)
                    varias      → cero o más claves
                    texto       → valores libres, sin claves (opcionalmente con PATRON)
                    vocabulario → no se pregunta: es la lista de ROLES de otra dimensión
    ROLES           nombre de una dimensión `vocabulario`: cada clave elegida lleva un rol
    REQUISITO       'DIM=clave1|clave2': solo se pregunta si el registro ya tiene esa etiqueta
                    (de una pasada anterior)
    PERMITE_NUEVAS  Sí/No: el LLM puede proponer claves nuevas (van a revisión, no al catálogo)
    PATRON          expresión regular para validar dimensiones `texto` (p. ej. ^[A-Z]{2}$)
    ES EN FR PT     nombre de la dimensión en cada idioma
    INSTRUCCION     qué debe decidir el LLM en esta dimensión
    ACTIVO          Sí/No

catalogo_clasificacion · una fila por clave
    DIMENSION CLAVE ES EN FR PT SINONIMOS DESCRIPCION ACTIVO
    CLAVE: minúsculas, números y guion bajo. Nunca se renombra: se desactiva y se crea otra.
    SINONIMOS: separados por ';' (las etiquetas en los otros idiomas ya cuentan como sinónimos).

Resultados:
    etiquetas              → una fila por etiqueta. estado: Pendiente / Aceptada / Rechazada / Reemplazada
    control_clasificacion  → una fila por (entidad, registro, pasada): cuándo se clasificó, huella del
                             texto y la columna `reclasificar` (poner Sí para volver a clasificar)
    propuestas_catalogo    → claves nuevas sugeridas por el LLM, para revisión humana

Qué se clasifica en cada corrida:
    · registros nuevos (sin fila en control_clasificacion para esa pasada)
    · registros con reclasificar = Sí
    · registros cuyo texto cambió, solo con si_cambia_texto=True (si no, solo se avisa)
    · todo lo indicado en `ids`, con forzar=True
    Al reclasificar, las etiquetas LLM Pendientes anteriores pasan a Reemplazada; las Aceptadas
    y Rechazadas (decisiones humanas) no se tocan.

Uso mínimo:
    cat = Catalogo.desde_hoja(sh)
    clf = Clasificador(cat, client, contexto='...', ruta_cache='cache.jsonl')
    clf.vista_previa(registro, campos, pasada=1)                     # sin costo
    res = clf.clasificar(df, 'id', campos, pasada=1, entidad='articulos',
                         previas=leer_tabla(sh, 'etiquetas'),
                         control=leer_tabla(sh, 'control_clasificacion'), limite=3)
    guardar_corrida(sh, res)
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

__version__ = '0.2'

# ---------------------------------------------------------------------------
# 1. Constantes
# ---------------------------------------------------------------------------

COLS_DIMENSIONES = ['DIMENSION', 'ORDEN', 'PASADA', 'CARDINALIDAD', 'ROLES', 'REQUISITO',
                    'PERMITE_NUEVAS', 'PATRON', 'ES', 'EN', 'FR', 'PT', 'INSTRUCCION', 'ACTIVO']
COLS_CATALOGO = ['DIMENSION', 'CLAVE', 'ES', 'EN', 'FR', 'PT', 'SINONIMOS', 'DESCRIPCION', 'ACTIVO']
COLS_ETIQUETAS = ['id_etiqueta', 'entidad', 'id_registro', 'dimension', 'clave', 'rol', 'origen', 'modelo',
                  'confianza', 'evidencia', 'estado', 'id_corrida', 'fecha', 'observacion']
COLS_PROPUESTAS = ['entidad', 'id_registro', 'dimension', 'clave_propuesta', 'etiqueta_es', 'justificacion',
                   'evidencia', 'modelo', 'id_corrida', 'fecha', 'estado', 'decision']
COLS_CONTROL = ['entidad', 'id_registro', 'pasada', 'id_corrida', 'fecha', 'modelo', 'huella',
                'n_etiquetas', 'motivo', 'reclasificar', 'nota']
ESTADOS = ['Pendiente', 'Aceptada', 'Rechazada', 'Reemplazada']

IDIOMAS = ['ES', 'EN', 'FR', 'PT']
CARDINALIDADES = {'una', 'varias', 'texto', 'vocabulario'}
SIN_INFO = 'no_determinable'
CONFIANZAS = ['alta', 'media', 'baja']

_CLAVE_OK = re.compile(r'^[a-z0-9_]+$')
_DIM_OK = re.compile(r'^[A-Z0-9_]+$')

SISTEMA_BASE = """Eres un asistente que clasifica trabajos de investigación según un catálogo cerrado.
{contexto}

Reglas:
1. Usa solo las claves del catálogo, escritas exactamente como aparecen entre comillas invertidas (`así`).
2. Básate solo en el texto entregado. No completes con lo que sepas de los autores ni del tema.
3. En `evidencia` copia literalmente un fragmento breve del texto (máximo 25 palabras), en su idioma original, que justifique la etiqueta.
4. `confianza`: alta = el texto lo dice explícitamente; media = se deduce con claridad; baja = indicio débil.
5. Si el texto no informa una dimensión, deja su lista vacía (o usa `{sin_info}` en las de una sola clave). Es mejor no etiquetar que adivinar.
6. Las claves que propongas y no estén en el catálogo van solo en `claves_nuevas`, nunca dentro de una dimensión.

# Catálogo

{catalogo}"""


# ---------------------------------------------------------------------------
# 2. Utilidades
# ---------------------------------------------------------------------------

def _norm(s):
    s = unicodedata.normalize('NFD', str(s))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower().strip()


def _si(x):
    return _norm(x) in {'si', 'true', '1', 'x', 'yes', 'oui', 'sim'}


def _partes(x, sep):
    return [p.strip() for p in str(x).split(sep) if p.strip()]


def _comparable(s):
    return re.sub(r'\W+', ' ', _norm(s)).strip()


def _ultimo_numero(serie):
    nums = pd.Series(serie, dtype=str).str.extract(r'(\d+)')[0].dropna()
    return int(nums.astype(int).max()) if len(nums) else 0


def _tabla(df, columnas, nombre):
    df = df.copy().fillna('').astype(str)
    df.columns = [str(c).strip().upper() for c in df.columns]
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise ValueError(f'{nombre}: faltan las columnas {", ".join(faltan)}')
    return df


# ---------------------------------------------------------------------------
# 3. Catálogo
# ---------------------------------------------------------------------------

@dataclass
class Clave:
    dimension: str
    clave: str
    etiquetas: dict
    sinonimos: list
    descripcion: str
    activa: bool


@dataclass
class Dimension:
    nombre: str
    orden: float
    pasada: int | None
    cardinalidad: str
    roles: str
    requisito: tuple | None          # (DIMENSION, {claves})
    permite_nuevas: bool
    patron: str
    etiquetas: dict
    instruccion: str


class Catalogo:
    """Catálogo de clasificación leído desde dos tablas. Valida al construirse."""

    def __init__(self, dimensiones: pd.DataFrame, claves: pd.DataFrame, estricto=True):
        self.tabla_dimensiones = _tabla(dimensiones, COLS_DIMENSIONES, 'catalogo_dimensiones')
        self.tabla_claves = _tabla(claves, COLS_CATALOGO, 'catalogo_clasificacion')
        self.errores, self.avisos = [], []
        self.dimensiones: dict[str, Dimension] = {}
        self.claves: dict[str, dict[str, Clave]] = {}     # solo activas, de dimensiones activas
        self._todas: dict[tuple, Clave] = {}               # todas, para mostrar etiquetas antiguas

        nombres_tabla = set()
        for _, r in self.tabla_dimensiones.iterrows():
            nombre = r['DIMENSION'].strip()
            if not nombre:
                continue
            if nombre in nombres_tabla:
                self.errores.append(f'Dimensión repetida: {nombre}')
                continue
            nombres_tabla.add(nombre)
            if not _si(r['ACTIVO']):
                continue
            requisito = None
            if r['REQUISITO'].strip():
                if '=' not in r['REQUISITO']:
                    self.errores.append(f'{nombre}: REQUISITO debe tener la forma DIM=clave1|clave2')
                else:
                    d, cs = r['REQUISITO'].split('=', 1)
                    requisito = (d.strip(), set(_partes(cs, '|')))
            pasada = r['PASADA'].strip()
            try:
                orden = float(r['ORDEN'] or 0)
            except ValueError:
                orden = 0
            self.dimensiones[nombre] = Dimension(
                nombre=nombre, orden=orden,
                pasada=int(pasada) if pasada.isdigit() else None,
                cardinalidad=r['CARDINALIDAD'].strip().lower(),
                roles=r['ROLES'].strip(), requisito=requisito,
                permite_nuevas=_si(r['PERMITE_NUEVAS']), patron=r['PATRON'].strip(),
                etiquetas={i: r[i].strip() for i in IDIOMAS}, instruccion=r['INSTRUCCION'].strip())
            self.claves[nombre] = {}

        for _, r in self.tabla_claves.iterrows():
            dim, clave = r['DIMENSION'].strip(), r['CLAVE'].strip()
            if not dim and not clave:
                continue
            if dim not in nombres_tabla:
                self.errores.append(f'Clave "{clave}": la dimensión "{dim}" no existe')
                continue
            if not _CLAVE_OK.match(clave):
                self.errores.append(f'{dim}.{clave}: la clave solo admite minúsculas, números y _')
                continue
            if clave == SIN_INFO:
                self.errores.append(f'{dim}.{clave}: "{SIN_INFO}" es una clave reservada')
                continue
            if (dim, clave) in self._todas:
                self.errores.append(f'Clave repetida: {dim}.{clave}')
                continue
            c = Clave(dimension=dim, clave=clave, etiquetas={i: r[i].strip() for i in IDIOMAS},
                      sinonimos=_partes(r['SINONIMOS'], ';'), descripcion=r['DESCRIPCION'].strip(),
                      activa=_si(r['ACTIVO']))
            self._todas[(dim, clave)] = c
            if c.activa and dim in self.claves:
                self.claves[dim][clave] = c

        self._validar()
        if self.errores and estricto:
            raise ValueError('El catálogo tiene errores:\n  · ' + '\n  · '.join(self.errores))

    # --- construcción ---

    @classmethod
    def desde_csv(cls, ruta_dimensiones, ruta_claves, **kw):
        leer = lambda p: pd.read_csv(p, dtype=str, keep_default_na=False)
        return cls(leer(ruta_dimensiones), leer(ruta_claves), **kw)

    @classmethod
    def desde_hoja(cls, sh, pestana_dimensiones='catalogo_dimensiones',
                   pestana_claves='catalogo_clasificacion', **kw):
        return cls(leer_tabla(sh, pestana_dimensiones), leer_tabla(sh, pestana_claves), **kw)

    def guardar_csv(self, carpeta, prefijo='catalogo'):
        carpeta = Path(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)
        self.tabla_dimensiones[COLS_DIMENSIONES].to_csv(carpeta / f'{prefijo}_dimensiones.csv', index=False)
        self.tabla_claves[COLS_CATALOGO].to_csv(carpeta / f'{prefijo}_clasificacion.csv', index=False)

    # --- validación ---

    def _validar(self):
        E, A = self.errores, self.avisos
        for d in self.dimensiones.values():
            n = d.nombre
            if not _DIM_OK.match(n):
                E.append(f'{n}: el nombre de dimensión solo admite MAYÚSCULAS, números y _')
            if d.cardinalidad not in CARDINALIDADES:
                E.append(f'{n}: CARDINALIDAD "{d.cardinalidad}" no válida ({", ".join(sorted(CARDINALIDADES))})')
                continue
            if d.cardinalidad != 'vocabulario' and d.pasada is None:
                E.append(f'{n}: falta PASADA (número entero)')
            if d.cardinalidad in ('una', 'varias', 'vocabulario') and not self.claves.get(n):
                E.append(f'{n}: no tiene claves activas')
            if d.cardinalidad == 'texto' and self.claves.get(n):
                A.append(f'{n}: es de texto libre; sus claves no se usan')
            if d.roles:
                v = self.dimensiones.get(d.roles)
                if not v or v.cardinalidad != 'vocabulario':
                    E.append(f'{n}: ROLES "{d.roles}" debe ser una dimensión activa de tipo vocabulario')
            if d.requisito:
                rd, rc = d.requisito
                base = self.dimensiones.get(rd)
                if not base:
                    E.append(f'{n}: el REQUISITO usa "{rd}", que no es una dimensión activa')
                else:
                    faltan = rc - set(self.claves.get(rd, {}))
                    if faltan:
                        E.append(f'{n}: el REQUISITO usa claves inexistentes en {rd}: {", ".join(sorted(faltan))}')
                    if base.pasada is None or d.pasada is None or base.pasada >= d.pasada:
                        E.append(f'{n}: el REQUISITO debe referirse a una dimensión de una pasada anterior')
            if d.patron:
                try:
                    re.compile(d.patron)
                except re.error as e:
                    E.append(f'{n}: PATRON no válido ({e})')
            faltan = [i for i in IDIOMAS if not d.etiquetas.get(i)]
            if faltan:
                A.append(f'{n}: falta el nombre en {", ".join(faltan)}')
        for dim, cs in self.claves.items():
            for c in cs.values():
                faltan = [i for i in IDIOMAS if not c.etiquetas.get(i)]
                if faltan:
                    A.append(f'{dim}.{c.clave}: falta la etiqueta en {", ".join(faltan)}')

    # --- consultas ---

    def pasadas(self):
        return sorted({d.pasada for d in self.dimensiones.values() if d.pasada is not None})

    def de_pasada(self, pasada):
        dims = [d for d in self.dimensiones.values()
                if d.pasada == pasada and d.cardinalidad != 'vocabulario']
        return sorted(dims, key=lambda d: (d.orden, d.nombre))

    def cumple_requisito(self, d, etiquetas_registro):
        """etiquetas_registro: {dimension: {claves}} del registro."""
        if not d.requisito:
            return True
        rd, rc = d.requisito
        return bool(set(etiquetas_registro.get(rd, set())) & rc)

    def etiqueta(self, dimension, clave, idioma='ES'):
        """Etiqueta visible de una clave (también de claves desactivadas)."""
        c = self._todas.get((dimension, clave))
        if not c:
            return clave
        return c.etiquetas.get(idioma) or c.etiquetas.get('ES') or clave

    def resumen(self):
        filas = []
        for d in sorted(self.dimensiones.values(), key=lambda d: (d.pasada or 99, d.orden)):
            filas.append({'DIMENSION': d.nombre, 'PASADA': d.pasada or '', 'CARDINALIDAD': d.cardinalidad,
                          'claves': len(self.claves.get(d.nombre, {})), 'ROLES': d.roles,
                          'REQUISITO': f'{d.requisito[0]}={"|".join(sorted(d.requisito[1]))}' if d.requisito else '',
                          'nuevas': 'Sí' if d.permite_nuevas else ''})
        return pd.DataFrame(filas)

    # --- prompt y esquema ---

    def _nombre(self, c, idioma):
        return c.etiquetas.get(idioma) or c.etiquetas.get('ES') or c.clave

    def describir(self, d, idioma='ES'):
        """Texto de una dimensión para el prompt."""
        lineas = [f'## {d.nombre} ({d.etiquetas.get(idioma) or d.nombre})']
        if d.instruccion:
            lineas.append(d.instruccion)
        lineas.append({'una': f'Elige exactamente una clave; usa `{SIN_INFO}` si el texto no permite decidir.',
                       'varias': 'Elige todas las claves que correspondan (puede ser ninguna).',
                       'texto': 'Escribe valores libres (puede ser ninguno).'}[d.cardinalidad])
        if d.patron:
            lineas.append(f'Cada valor debe cumplir el patrón {d.patron}.')
        if d.roles:
            roles = '; '.join(f'`{c.clave}` = {self._nombre(c, idioma)}'
                              + (f' ({c.descripcion})' if c.descripcion else '')
                              for c in self.claves[d.roles].values())
            lineas.append(f'Cada clave lleva un rol: {roles}.')
        if d.cardinalidad != 'texto':
            for c in self.claves[d.nombre].values():
                principal = self._nombre(c, idioma)
                otros = [c.etiquetas[i] for i in IDIOMAS if i != idioma and c.etiquetas.get(i)] + c.sinonimos
                otros = list(dict.fromkeys(o for o in otros if _norm(o) != _norm(principal)))
                linea = f'- `{c.clave}`: {principal}'
                if c.descripcion:
                    linea += f' — {c.descripcion}'
                if otros:
                    linea += f' [también: {"; ".join(otros)}]'
                lineas.append(linea)
        if d.permite_nuevas:
            lineas.append('Si falta un concepto importante, propónlo en `claves_nuevas`.')
        return '\n'.join(lineas)

    def esquema(self, dims):
        """Esquema JSON (modo estricto de OpenAI) para las dimensiones dadas."""
        def objeto(props):
            return {'type': 'object', 'properties': props, 'required': list(props),
                    'additionalProperties': False}
        texto = {'type': 'string'}
        conf = {'type': 'string', 'enum': CONFIANZAS}
        props = {}
        for d in dims:
            if d.cardinalidad == 'texto':
                item = objeto({'evidencia': texto, 'valor': texto, 'confianza': conf})
            else:
                claves = list(self.claves[d.nombre]) + ([SIN_INFO] if d.cardinalidad == 'una' else [])
                p = {'evidencia': texto, 'clave': {'type': 'string', 'enum': claves}}
                if d.roles:
                    p['rol'] = {'type': 'string', 'enum': list(self.claves[d.roles])}
                p['confianza'] = conf
                item = objeto(p)
            props[d.nombre] = item if d.cardinalidad == 'una' else {'type': 'array', 'items': item}
        nuevas = [d.nombre for d in dims if d.permite_nuevas]
        if nuevas:
            props['claves_nuevas'] = {'type': 'array', 'items': objeto({
                'dimension': {'type': 'string', 'enum': nuevas}, 'clave_propuesta': texto,
                'etiqueta_es': texto, 'justificacion': texto, 'evidencia': texto})}
        return objeto(props)


# ---------------------------------------------------------------------------
# 4. Etiquetas previas
# ---------------------------------------------------------------------------

def _filtrar_entidad(df, entidad):
    if df is None or df.empty or not entidad or 'entidad' not in df.columns:
        return df
    return df[df['entidad'] == entidad]


def indice_etiquetas(etiquetas, incluir_pendientes=True):
    """{id_registro: {dimension: {claves}}}. Si una dimensión tiene etiquetas Aceptadas,
    se usan solo esas; si no, las Pendientes (cuando incluir_pendientes=True).
    Rechazadas y Reemplazadas no cuentan."""
    idx = {}
    if etiquetas is None or etiquetas.empty:
        return idx
    estados = ['Aceptada', 'Pendiente'] if incluir_pendientes else ['Aceptada']
    e = etiquetas[etiquetas['estado'].isin(estados)]
    for (i, d), g in e.groupby(['id_registro', 'dimension']):
        acept = g[g['estado'] == 'Aceptada']
        idx.setdefault(i, {})[d] = set((acept if len(acept) else g)['clave'])
    return idx


@dataclass
class Resultado:
    """Lo que devuelve una corrida. No está guardado hasta llamar a guardar_corrida()."""
    entidad: str
    pasada: int
    id_corrida: str
    etiquetas: pd.DataFrame
    propuestas: pd.DataFrame
    errores: pd.DataFrame
    control: pd.DataFrame
    reemplazar: list = field(default_factory=list)   # id_etiqueta que pasan a Reemplazada

    def __repr__(self):
        return (f'Resultado {self.id_corrida} · {self.entidad} · pasada {self.pasada}: '
                f'{len(self.control)} registros, {len(self.etiquetas)} etiquetas, '
                f'{len(self.propuestas)} propuestas, {len(self.errores)} errores, '
                f'{len(self.reemplazar)} etiquetas a reemplazar')


# ---------------------------------------------------------------------------
# 5. Clasificador
# ---------------------------------------------------------------------------

class Clasificador:
    """Arma el prompt desde el catálogo, llama a la API de OpenAI con salida JSON estricta
    y devuelve etiquetas en formato largo. Guarda cada respuesta en un caché (JSONL)
    para no pagar dos veces la misma consulta."""

    def __init__(self, catalogo, client, contexto='', modelo='gpt-4o-mini', temperatura=0,
                 ruta_cache=None, max_caracteres=3000, idioma_prompt='ES', reintentos=3):
        self.cat, self.client, self.contexto = catalogo, client, contexto
        self.modelo, self.temperatura = modelo, temperatura
        self.max_caracteres, self.idioma, self.reintentos = max_caracteres, idioma_prompt, reintentos
        self.ruta_cache = Path(ruta_cache) if ruta_cache else None
        self.cache = {}
        if self.ruta_cache and self.ruta_cache.exists():
            for linea in self.ruta_cache.read_text(encoding='utf-8').splitlines():
                if linea.strip():
                    x = json.loads(linea)
                    self.cache[x['firma']] = x['respuesta']
        self.uso = {'llamadas': 0, 'desde_cache': 0, 'tokens_entrada': 0, 'tokens_salida': 0}

    # --- preparación ---

    def texto_registro(self, registro, campos):
        """campos: {'Etiqueta que ve el LLM': 'columna del registro', ...}"""
        partes = []
        for etiqueta, col in campos.items():
            valor = ' '.join(str(registro.get(col, '') or '').split())
            if valor:
                if len(valor) > self.max_caracteres:
                    valor = valor[:self.max_caracteres] + '…'
                partes.append(f'{etiqueta}: {valor}')
        return '\n'.join(partes)

    def huella(self, registro, campos):
        """Resumen corto del texto que ve el LLM: si cambia, cambió la entrada."""
        texto = self.texto_registro(registro, campos)
        return hashlib.sha256(texto.encode('utf-8')).hexdigest()[:12] if texto else ''

    def preparar(self, registro, campos, pasada, etiquetas_registro=None):
        dims = [d for d in self.cat.de_pasada(pasada)
                if self.cat.cumple_requisito(d, etiquetas_registro or {})]
        texto = self.texto_registro(registro, campos)
        if not dims or not texto:
            return None
        catalogo = '\n\n'.join(self.cat.describir(d, self.idioma) for d in dims)
        sistema = SISTEMA_BASE.format(contexto=self.contexto.strip(), catalogo=catalogo, sin_info=SIN_INFO)
        return {'dims': dims, 'sistema': sistema, 'usuario': texto, 'esquema': self.cat.esquema(dims)}

    def vista_previa(self, registro, campos, pasada, etiquetas_registro=None):
        """Muestra el prompt y el esquema sin llamar a la API."""
        p = self.preparar(registro, campos, pasada, etiquetas_registro)
        if p is None:
            print('Sin dimensiones aplicables (revisa REQUISITO) o el registro no tiene texto.')
            return None
        print('=== SISTEMA ===\n' + p['sistema'])
        print('\n=== USUARIO ===\n' + p['usuario'])
        print(f"\n=== ESQUEMA === dimensiones: {', '.join(d.nombre for d in p['dims'])}")
        print(f"Tamaño aproximado: {(len(p['sistema']) + len(p['usuario']) + len(json.dumps(p['esquema']))) // 4} tokens de entrada")
        return p

    # --- llamada ---

    def _llamar(self, p):
        firma = hashlib.sha256(json.dumps([self.modelo, p['sistema'], p['usuario'], p['esquema']],
                                          ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        if firma in self.cache:
            self.uso['desde_cache'] += 1
            return self.cache[firma]
        kw = {'model': self.modelo,
              'messages': [{'role': 'system', 'content': p['sistema']},
                           {'role': 'user', 'content': p['usuario']}],
              'response_format': {'type': 'json_schema',
                                  'json_schema': {'name': 'clasificacion', 'strict': True, 'schema': p['esquema']}}}
        if self.temperatura is not None:
            kw['temperature'] = self.temperatura
        for intento in range(self.reintentos):
            try:
                r = self.client.chat.completions.create(**kw)
                msg = r.choices[0].message
                if getattr(msg, 'refusal', None):
                    raise RuntimeError(f'el modelo se negó: {msg.refusal}')
                respuesta = json.loads(msg.content)
                break
            except Exception:
                if intento == self.reintentos - 1:
                    raise
                time.sleep(3 * 2 ** intento)
        self.uso['llamadas'] += 1
        if getattr(r, 'usage', None):
            self.uso['tokens_entrada'] += r.usage.prompt_tokens or 0
            self.uso['tokens_salida'] += r.usage.completion_tokens or 0
        self.cache[firma] = respuesta
        if self.ruta_cache:
            with self.ruta_cache.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'firma': firma, 'respuesta': respuesta}, ensure_ascii=False) + '\n')
        return respuesta

    # --- respuesta → filas ---

    def _a_filas(self, entidad, id_reg, p, resp, id_corrida):
        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        texto = _comparable(p['usuario'])
        base = {'entidad': entidad, 'id_registro': id_reg, 'origen': 'LLM', 'modelo': self.modelo, 'estado': 'Pendiente',
                'id_corrida': id_corrida, 'fecha': t}
        filas = []
        for d in p['dims']:
            valor = resp.get(d.nombre)
            items = [valor] if d.cardinalidad == 'una' else (valor or [])
            vistos = set()
            for it in items:
                if not it:
                    continue
                clave = (' '.join(str(it.get('valor', '')).split()) if d.cardinalidad == 'texto'
                         else str(it.get('clave', '')).strip())
                rol = str(it.get('rol', '')).strip()
                if not clave or (clave, rol) in vistos:
                    continue
                vistos.add((clave, rol))
                obs = []
                if d.cardinalidad == 'texto' and d.patron and not re.fullmatch(d.patron, clave):
                    obs.append('no cumple el patrón')
                ev = str(it.get('evidencia', '')).strip()
                if ev and _comparable(ev) not in texto:
                    obs.append('evidencia no literal')
                filas.append({**base, 'dimension': d.nombre, 'clave': clave, 'rol': rol,
                              'confianza': it.get('confianza', ''), 'evidencia': ev,
                              'observacion': '; '.join(obs)})
        propuestas = [{'entidad': entidad, 'id_registro': id_reg, 'dimension': x.get('dimension', ''),
                       'clave_propuesta': x.get('clave_propuesta', ''), 'etiqueta_es': x.get('etiqueta_es', ''),
                       'justificacion': x.get('justificacion', ''), 'evidencia': x.get('evidencia', ''),
                       'modelo': self.modelo, 'id_corrida': id_corrida, 'fecha': t,
                       'estado': 'Pendiente', 'decision': ''}
                      for x in (resp.get('claves_nuevas') or [])]
        return filas, propuestas

    # --- corrida ---

    def clasificar(self, registros, col_id, campos, pasada, entidad='', previas=None, control=None,
                   ids=None, forzar=False, si_cambia_texto=False, incluir_pendientes=True,
                   limite=None, id_corrida=None):
        """Clasifica en una pasada los registros que lo necesitan (ver el encabezado del módulo).
        registros: DataFrame · col_id: columna con el ID · campos: {'Etiqueta': 'columna'}
        entidad: nombre de la pestaña o tipo de registro (publicaciones, tesis…)
        previas: pestaña `etiquetas` · control: pestaña `control_clasificacion`
        ids: limitar a estos IDs · forzar: reclasificar los indicados aunque ya estén hechos
        Devuelve un Resultado. No escribe nada: para eso, guardar_corrida()."""
        previas = _filtrar_entidad(previas, entidad)
        control = _filtrar_entidad(control, entidad)
        indice = indice_etiquetas(previas, incluir_pendientes)
        hechos = {}
        if control is not None and not control.empty:
            c = control[control['pasada'].astype(str) == str(pasada)]
            hechos = {r['id_registro']: r for _, r in c.iterrows()}
        id_corrida = id_corrida or f'{entidad or "reg"}_p{pasada}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:4]}'
        df = registros if ids is None else registros[registros[col_id].isin(set(ids))]

        cola, cambiados = [], []
        for _, r in df.iterrows():
            i, h = r[col_id], self.huella(r, campos)
            c = hechos.get(i)
            if forzar:
                motivo = 'forzado'
            elif c is None:
                motivo = 'nuevo'
            elif _si(c.get('reclasificar', '')):
                motivo = 'solicitado'
            elif h and c.get('huella', '') and c.get('huella') != h:
                if not si_cambia_texto:
                    cambiados.append(i)
                    continue
                motivo = 'texto_cambio'
            else:
                continue
            cola.append((r, h, motivo))
        if limite:
            cola = cola[:limite]
        conteo = Counter(m for *_, m in cola)
        print(f'Pasada {pasada} · {entidad or "registros"} · {len(cola)} por clasificar '
              f'({", ".join(f"{k}: {v}" for k, v in conteo.items()) or "nada pendiente"}) · '
              f'{len(df) - len(cola) - len(cambiados)} ya clasificados u omitidos por el límite')
        if cambiados:
            print(f'ℹ️  {len(cambiados)} ya clasificados cambiaron de texto y NO se reclasifican '
                  f'(usa si_cambia_texto=True o marca reclasificar = Sí)')

        dims_pasada = {d.nombre for d in self.cat.de_pasada(pasada)}
        anteriores = pd.DataFrame()
        if previas is not None and not previas.empty and 'id_etiqueta' in previas.columns:
            anteriores = previas[previas['dimension'].isin(dims_pasada) & (previas['origen'] == 'LLM')
                                 & (previas['estado'] == 'Pendiente')]

        filas, propuestas, errores, control_filas, reemplazar, sin_dims = [], [], [], [], [], 0
        for n, (r, h, motivo) in enumerate(cola, 1):
            id_reg = r[col_id]
            p = self.preparar(r, campos, pasada, indice.get(id_reg, {}))
            if p is None:
                sin_dims += 1
                continue
            try:
                resp = self._llamar(p)
            except Exception as e:
                errores.append({'id_registro': id_reg, 'error': str(e)[:300]})
                continue
            f, pr = self._a_filas(entidad, id_reg, p, resp, id_corrida)
            filas += f
            propuestas += pr
            control_filas.append({'entidad': entidad, 'id_registro': id_reg, 'pasada': str(pasada),
                                  'id_corrida': id_corrida, 'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                  'modelo': self.modelo, 'huella': h, 'n_etiquetas': str(len(f)),
                                  'motivo': motivo, 'reclasificar': '', 'nota': ''})
            if len(anteriores):
                reemplazar += anteriores.loc[anteriores['id_registro'] == id_reg, 'id_etiqueta'].tolist()
            if n % 10 == 0 or n == len(cola):
                print(f'  {n}/{len(cola)} · {self.uso}')

        if sin_dims:
            print(f'{sin_dims} registros sin dimensiones aplicables (no cumplen el REQUISITO) o sin texto')
        if errores:
            print(f'⚠️  {len(errores)} errores (se reintentarán en la próxima corrida)')
        return Resultado(entidad, pasada, id_corrida,
                         pd.DataFrame(filas, columns=COLS_ETIQUETAS),
                         pd.DataFrame(propuestas, columns=COLS_PROPUESTAS),
                         pd.DataFrame(errores, columns=['id_registro', 'error']),
                         pd.DataFrame(control_filas, columns=COLS_CONTROL), reemplazar)


# ---------------------------------------------------------------------------
# 6. Google Sheets (gspread se importa solo si se usan estas funciones)
# ---------------------------------------------------------------------------

def leer_tabla(sh, pestana):
    """Pestaña como DataFrame de texto. Vacío si no existe."""
    import gspread
    try:
        valores = sh.worksheet(pestana).get_all_values()
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    return pd.DataFrame(valores[1:], columns=valores[0]) if valores else pd.DataFrame()


def escribir_tabla(sh, pestana, df, sobrescribir=False):
    """Crea la pestaña con df. Si ya existe y no se pide sobrescribir, no la toca."""
    import gspread
    try:
        ws = sh.worksheet(pestana)
        if not sobrescribir:
            print(f'"{pestana}" ya existe; no se modifica (usa sobrescribir=True para reemplazarla).')
            return ws
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(pestana, rows=len(df) + 50, cols=max(len(df.columns), 1))
    if ws.row_count < len(df) + 1:
        ws.add_rows(len(df) + 1 - ws.row_count)
    if ws.col_count < len(df.columns):
        ws.add_cols(len(df.columns) - ws.col_count)
    df = df.fillna('').astype(str)
    ws.update(values=[df.columns.tolist()] + df.values.tolist(), range_name='A1', value_input_option='RAW')
    ws.freeze(rows=1)
    print(f'"{pestana}": {len(df)} filas escritas.')
    return ws


def agregar_filas(sh, pestana, df, columnas=None):
    """Agrega filas al final, alineadas con el encabezado real de la hoja."""
    import gspread
    if df is None or df.empty:
        print(f'"{pestana}": nada que agregar.')
        return None
    columnas = list(columnas or df.columns)
    try:
        ws = sh.worksheet(pestana)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(pestana, rows=max(1000, len(df) + 10), cols=len(columnas))
        ws.update(values=[columnas], range_name='A1')
        ws.freeze(rows=1)
    encabezado = ws.row_values(1)
    if not encabezado:
        ws.update(values=[columnas], range_name='A1')
        encabezado = columnas
    ws.append_rows(df.reindex(columns=encabezado, fill_value='').fillna('').astype(str).values.tolist(),
                   value_input_option='RAW', table_range='A1')
    print(f'"{pestana}": {len(df)} filas agregadas.')
    return ws


def _desplegable(sh, ws, columna, valores, estricto=True):
    enc = ws.row_values(1)
    if columna not in enc:
        return
    i = enc.index(columna)
    sh.batch_update({'requests': [{'setDataValidation': {
        'range': {'sheetId': ws.id, 'startRowIndex': 1, 'endRowIndex': ws.row_count,
                  'startColumnIndex': i, 'endColumnIndex': i + 1},
        'rule': {'condition': {'type': 'ONE_OF_LIST', 'values': [{'userEnteredValue': v} for v in valores]},
                 'showCustomUi': True, 'strict': estricto}}}]})


def guardar_etiquetas(sh, etiquetas, pestana='etiquetas', previas=None):
    """Numera las etiquetas (etq_000001…) a continuación de las existentes y las agrega."""
    if etiquetas is None or etiquetas.empty:
        print(f'"{pestana}": nada que agregar.')
        return None
    previas = leer_tabla(sh, pestana) if previas is None else previas
    ultimo = _ultimo_numero(previas['id_etiqueta']) if 'id_etiqueta' in previas.columns else 0
    etiquetas = etiquetas.copy()
    etiquetas['id_etiqueta'] = [f'etq_{ultimo + i:06d}' for i in range(1, len(etiquetas) + 1)]
    ws = agregar_filas(sh, pestana, etiquetas, COLS_ETIQUETAS)
    _desplegable(sh, ws, 'estado', ESTADOS)
    return ws


def marcar_estado(sh, pestana, ids_etiqueta, estado):
    """Cambia el estado de las etiquetas indicadas (por id_etiqueta)."""
    import gspread
    objetivo = set(ids_etiqueta)
    if not objetivo:
        return
    ws = sh.worksheet(pestana)
    valores = ws.get_all_values()
    enc = valores[0]
    ci, ii = enc.index('estado') + 1, enc.index('id_etiqueta')
    cambios = [{'range': gspread.utils.rowcol_to_a1(n, ci), 'values': [[estado]]}
               for n, fila in enumerate(valores[1:], 2) if len(fila) > ii and fila[ii] in objetivo]
    if cambios:
        ws.batch_update(cambios, value_input_option='RAW')
    print(f'"{pestana}": {len(cambios)} etiquetas → {estado}.')


def actualizar_control(sh, nuevo, pestana='control_clasificacion'):
    """Inserta o reemplaza filas (entidad, id_registro, pasada). Conserva `nota` y las columnas
    que hayas agregado a mano; deja `reclasificar` vacío en lo recién clasificado."""
    if nuevo is None or nuevo.empty:
        print(f'"{pestana}": nada que actualizar.')
        return None
    clave = ['entidad', 'id_registro', 'pasada']
    nuevo = nuevo.fillna('').astype(str).copy()
    previo = leer_tabla(sh, pestana)
    if previo.empty:
        tabla = nuevo
    else:
        for c in COLS_CONTROL:
            if c not in previo.columns:
                previo[c] = ''
        k = lambda d: list(map(tuple, d[clave].values))
        notas = dict(zip(k(previo), previo['nota']))
        nuevo['nota'] = [notas.get(x, '') for x in k(nuevo)]
        nuevas = set(k(nuevo))
        tabla = pd.concat([previo[[x not in nuevas for x in k(previo)]], nuevo], ignore_index=True)
        tabla = tabla.reindex(columns=list(previo.columns), fill_value='')
    ws = escribir_tabla(sh, pestana, tabla.fillna(''), sobrescribir=True)
    _desplegable(sh, ws, 'reclasificar', ['Sí'], estricto=False)
    return ws


def guardar_corrida(sh, res, pestana_etiquetas='etiquetas', pestana_control='control_clasificacion',
                    pestana_propuestas='propuestas_catalogo'):
    """Guarda un Resultado: agrega etiquetas, marca Reemplazada las anteriores, actualiza el control
    y agrega las propuestas. Si esa corrida ya se guardó, no hace nada."""
    previas = leer_tabla(sh, pestana_etiquetas)
    control = leer_tabla(sh, pestana_control)
    for t in (previas, control):
        if 'id_corrida' in t.columns and (t['id_corrida'] == res.id_corrida).any():
            print(f'La corrida {res.id_corrida} ya estaba guardada; no se hace nada.')
            return
    guardar_etiquetas(sh, res.etiquetas, pestana_etiquetas, previas=previas)
    if res.reemplazar:
        marcar_estado(sh, pestana_etiquetas, res.reemplazar, 'Reemplazada')
    actualizar_control(sh, res.control, pestana_control)
    agregar_filas(sh, pestana_propuestas, res.propuestas, COLS_PROPUESTAS)
