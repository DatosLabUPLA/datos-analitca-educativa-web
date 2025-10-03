# 🔗 URLs Amigables para Proyectos

## Resumen de Cambios

Se ha implementado un sistema de URLs amigables (slugs) para los proyectos, permitiendo acceder a ellos mediante URLs más descriptivas y fáciles de recordar.

### Antes:
```
http://localhost:3000/proyecto.html?id=2
```

### Ahora:
```
http://localhost:3000/proyecto.html?slug=cartografia-educacion-y-movimientos-sociales
```

---

## 📋 Cambios en Google Sheets

### 1. Nueva Columna en la Hoja "proyectos"

Debes agregar una columna llamada **`slug`** en tu Google Sheet (hoja "proyectos").

**Ubicación sugerida:** Después de la columna `ID_proyecto`

#### Ejemplo de tabla actualizada:

| id | proyecto | ID_proyecto | **slug** | tipo | anio | ... |
|----|----------|-------------|----------|------|------|-----|
| 1 | Mapas Colegresivo Educación Matemática | p0001 | mapas-congresivo-educacion-matematica | p0001 | 2023 | ... |
| 2 | Cartografía Educación y Movimientos Sociales | CEMS | cartografia-educacion-y-movimientos-sociales | Proyecto | 2023 | ... |
| 3 | Análisis de 37 revistas de educación matemática | RCL01 | analisis-37-revistas-educacion-matematica | Proyecto | 2023 | ... |

### 2. Reglas para crear Slugs

✅ **Formato correcto:**
- Solo letras minúsculas
- Sin acentos ni caracteres especiales
- Palabras separadas por guiones (`-`)
- Sin espacios
- Debe ser único (no repetir slugs)

✅ **Ejemplos válidos:**
- `proyecto-fondecyt-11230953`
- `cartografia-educacion-y-movimientos-sociales`
- `robotica-educativa-latinoamerica`

❌ **Ejemplos NO válidos:**
- `Proyecto Fondecyt` (espacios, mayúsculas)
- `cartografía_educación` (acentos, guiones bajos)
- `Proyecto 2023!!!` (caracteres especiales)

### 3. Campo Opcional

⚠️ **Importante:** El campo `slug` es **OPCIONAL**

- Si **NO** agregas un slug, el proyecto seguirá funcionando con el ID: `proyecto.html?id=2`
- Si **SÍ** agregas un slug, se usará automáticamente: `proyecto.html?slug=cartografia-educacion-y-movimientos-sociales`

---

## 🖥️ Cambios en el Código

### API (datos-analitica-educativa-api)

#### Nuevo Endpoint:

```python
GET /projects/slug/{slug}
```

**Ejemplo:**
```
https://api.datoseducativos.cl/projects/slug/cartografia-educacion-y-movimientos-sociales
```

Este endpoint busca un proyecto por su slug en lugar de por su ID numérico.

#### Endpoint existente (sigue funcionando):
```python
GET /projects/{project_id}
```

### Frontend (datos-analitca-educativa-web)

#### Cambios en `src/js/scripts.js`:

1. **Detección automática de slug o id:**
   - El código detecta si la URL tiene `?slug=xxx` o `?id=X`
   - Hace la petición correspondiente a la API

2. **Generación de enlaces:**
   - Si un proyecto tiene slug, genera: `/proyecto.html?slug=xxx`
   - Si NO tiene slug, genera: `/proyecto.html?id=X`

---

## 🚀 Cómo Usar

### Para agregar URLs amigables a tus proyectos:

1. **Abre tu Google Sheet** (hoja "proyectos")

2. **Agrega la columna `slug`** si no existe

3. **Completa los slugs** para cada proyecto:
   ```
   Ejemplo: "Cartografía Educación y Movimientos Sociales"
   Slug: "cartografia-educacion-y-movimientos-sociales"
   ```

4. **Despliega los cambios:**
   - Haz commit y push al repositorio de la API (si modificaste)
   - Haz commit y push al repositorio del frontend
   - GitHub Actions compilará y desplegará automáticamente

5. **Prueba las URLs:**
   ```
   https://datoseducativos.cl/proyecto.html?slug=tu-slug-aqui
   ```

---

## 🔄 Compatibilidad hacia atrás

✅ **Las URLs antiguas siguen funcionando:**

```
proyecto.html?id=2  ← Sigue funcionando
proyecto.html?slug=cartografia-educacion-y-movimientos-sociales  ← Nueva forma
```

---

## 💡 Consejos

### Generar slugs automáticamente desde el título:

Puedes usar esta fórmula en Google Sheets para generar slugs automáticamente:

```excel
=LOWER(REGEXREPLACE(REGEXREPLACE(B2,"[áàâãäåæ]","a"),"[^a-z0-9]+","-"))
```

Donde `B2` es la celda con el nombre del proyecto.

### Herramienta online:

También puedes usar herramientas como:
- https://slugify.online/
- Simplemente pega el título y copia el slug generado

---

## 📝 Checklist de Implementación

### En Google Sheets:
- [ ] Agregar columna `slug` en la hoja "proyectos"
- [ ] Completar slugs para los proyectos que quieras que tengan URL amigable
- [ ] Verificar que no haya slugs duplicados

### En la API:
- [x] Agregar endpoint `/projects/slug/{slug}`
- [ ] Hacer commit y push de los cambios
- [ ] Verificar que la API esté desplegada

### En el Frontend:
- [x] Modificar `scripts.js` para detectar slugs
- [x] Modificar generación de enlaces
- [ ] Hacer commit y push de los cambios
- [ ] Esperar el deploy automático de GitHub Actions

### Pruebas:
- [ ] Probar URL con slug: `proyecto.html?slug=xxx`
- [ ] Verificar que URL con ID siga funcionando: `proyecto.html?id=2`
- [ ] Verificar que los enlaces en la página principal usen slugs

---

## ❓ Preguntas Frecuentes

### ¿Puedo cambiar un slug después de crearlo?

Sí, pero considera que:
- Los enlaces antiguos con ese slug dejarán de funcionar
- Es mejor mantener los slugs consistentes

### ¿Qué pasa si no agrego slug a un proyecto?

No hay problema, seguirá funcionando con el ID numérico tradicional.

### ¿Los slugs deben estar en inglés o español?

Puedes usar el idioma que prefieras, pero es recomendable:
- Usar el idioma principal del proyecto
- Mantener consistencia en todos los proyectos

### ¿Puedo usar números en los slugs?

Sí, los números son válidos: `proyecto-fondecyt-11230953`

---

## 🛠️ Solución de Problemas

### Error: "No se proporcionó ni id ni slug en la URL"

**Causa:** La URL no tiene ni `?id=X` ni `?slug=xxx`

**Solución:** Asegúrate de que la URL tenga uno de estos parámetros:
```
✅ proyecto.html?id=2
✅ proyecto.html?slug=mi-proyecto
❌ proyecto.html
```

### El proyecto no se encuentra con el slug

**Posibles causas:**
1. El slug no existe en Google Sheets
2. Hay un error tipográfico en el slug
3. La API no se ha actualizado

**Solución:**
1. Verifica que el slug esté correctamente escrito en Google Sheets
2. Verifica que la columna se llame exactamente `slug` (sin espacios)
3. Prueba la API directamente: `https://api.datoseducativos.cl/projects/slug/tu-slug`

---

## 📞 Soporte

Si tienes problemas con la implementación:
1. Verifica que hayas seguido todos los pasos del checklist
2. Revisa los logs de GitHub Actions para ver si hay errores en el build
3. Prueba la API directamente para verificar que devuelve los datos correctos
