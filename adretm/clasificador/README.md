# clasificador (ADRETM)

Clasifica registros bibliográficos (artículos, tesis, proyectos…) con un LLM a partir de un
catálogo cerrado que se edita en una hoja de Google Sheets.

```
clasificador_llm.py          módulo genérico (no depende del tema)
catalogos/etm/               catálogo semilla de ADRETM (ETM) y el script que lo genera
cuadernos/                   cuadernos de Colab que usan el módulo
```

## Uso en Colab

1. Descargar `clasificador_llm.py` desde GitHub y agregarlo a `sys.path` (celda 1 de `cuadernos/2_ADRETM_Clasificar_LLM.ipynb`).
2. Leer el catálogo desde la hoja: `cat = cl.Catalogo.desde_hoja(sh)`.
3. Clasificar: `res = clf.clasificar(df, col_id, campos, pasada, entidad=..., previas=..., control=...)`.
4. Revisar `res` y guardar: `cl.guardar_corrida(sh, res)`.

La documentación de las columnas del catálogo y de la lógica de reclasificación está al comienzo
de `clasificador_llm.py`.

## Otro tema

Crear `catalogos/<tema>/` con sus dos CSV (mismas columnas), subirlos a una hoja con
`escribir_tabla` y cambiar `CONTEXTO` y `CAMPOS` en el cuaderno. El módulo no cambia.
