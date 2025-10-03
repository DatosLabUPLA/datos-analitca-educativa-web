# 🔧 Solución para Heroku + Nginx

## ✅ Problema Identificado

Tu sitio está desplegado en **Heroku con PHP + Nginx**, no en GitHub Pages ni Cloudflare. Por eso las soluciones anteriores no funcionaban.

## 🎯 Solución Correcta

He creado un archivo de configuración de Nginx para Heroku que maneja los rewrites correctamente.

### Archivos Modificados:

1. **`custom_files/nginx_app.conf`** ⭐ (NUEVO - MÁS IMPORTANTE)
   ```nginx
   location / {
       # Rewrite para URLs de proyecto
       rewrite ^/proyecto/([a-zA-Z0-9\-]+)/?$ /proyecto.html?slug=$1 last;
   }
   ```

2. **`custom_files/Procfile`** (ACTUALIZADO)
   ```
   web: heroku-php-nginx -C nginx_app.conf
   ```

3. **`.github/workflows/static.yml`** (ACTUALIZADO)
   - Copia el 404.html a custom_files también

## 🚀 Cómo Funciona

```
Usuario visita: /proyecto/cartografia-educacion-y-movimientos-sociales
                              ↓
        Nginx intercepta la petición y hace rewrite
                              ↓
        Sirve: /proyecto.html?slug=cartografia-educacion-y-movimientos-sociales
                              ↓
        JavaScript detecta el slug y carga el proyecto desde la API
```

## 📋 Pasos para Activar

### 1. Commit y Push

```bash
git add .
git commit -m "Configurar Nginx rewrites para URLs amigables en Heroku"
git push origin main
```

### 2. Esperar Deploy

- GitHub Actions compilará el sitio
- Los archivos se copiarán a `dist/`
- Heroku detectará los cambios en `Procfile` y `nginx_app.conf`
- Heroku redesplegará con la nueva configuración de Nginx

⏱️ **Tiempo estimado:** 3-5 minutos

### 3. Verificar

Después del deploy, prueba estas URLs:

```
✅ https://datoseducativos.cl/proyecto/cartografia-educacion-y-movimientos-sociales
✅ https://datoseducativos.cl/proyecto/mapas-congresos-educacion-matematica  
✅ https://datoseducativos.cl/proyecto.html?id=2 (backward compatible)
```

## 🔍 Debug

Si sigue sin funcionar, verifica:

### 1. Heroku Logs

```bash
heroku logs --tail --app tu-app-name
```

Busca errores relacionados con Nginx.

### 2. Verifica que nginx_app.conf se cargó

```bash
heroku run bash --app tu-app-name
ls -la /app
cat /app/nginx_app.conf
```

### 3. Verifica la configuración de Nginx activa

Los logs de Heroku mostrarán si hay errores de sintaxis en `nginx_app.conf`.

## ⚙️ Cómo Funciona el Rewrite

```nginx
rewrite ^/proyecto/([a-zA-Z0-9\-]+)/?$ /proyecto.html?slug=$1 last;
```

**Explicación:**
- `^/proyecto/` - Comienza con /proyecto/
- `([a-zA-Z0-9\-]+)` - Captura el slug (letras, números, guiones)
- `/?$` - Opcional slash al final
- `/proyecto.html?slug=$1` - Reescribe a proyecto.html con el slug como parámetro
- `last` - Para el procesamiento de rewrites

## 📝 Notas Importantes

### El rewrite es transparente:

- **URL en el navegador:** `/proyecto/mi-slug` (NO cambia)
- **URL que recibe el servidor:** `/proyecto.html?slug=mi-slug`
- **JavaScript recibe:** El parámetro `slug` en `window.location.search`

### Compatibilidad:

- ✅ `/proyecto/slug` - Nueva forma (URLs limpias)
- ✅ `/proyecto.html?slug=slug` - También funciona
- ✅ `/proyecto.html?id=2` - Backward compatible

## 🆘 Solución de Problemas

### Problema: "Application Error" en Heroku

**Causa:** Error de sintaxis en `nginx_app.conf`

**Solución:** Revisa los logs de Heroku y verifica la sintaxis del archivo.

### Problema: Sigue mostrando 404

**Causa:** El archivo `nginx_app.conf` no se está aplicando

**Solución:** 
1. Verifica que el `Procfile` tenga: `web: heroku-php-nginx -C nginx_app.conf`
2. Verifica que ambos archivos estén en la raíz del deploy (custom_files se copia a dist)

### Problema: Nginx no encuentra proyecto.html

**Causa:** Los archivos no están en la ubicación correcta

**Solución:** Verifica que después del build, `proyecto.html` esté en `dist/proyecto.html`

## 🔄 Alternativa: Si Nginx no funciona

Si por alguna razón Nginx rewrites no funciona, podemos usar PHP para hacer el routing:

Crea `custom_files/.htaccess` (si Heroku soporta Apache):
```apache
RewriteEngine On
RewriteRule ^proyecto/([a-zA-Z0-9\-]+)/?$ proyecto.html?slug=$1 [L,QSA]
```

O crea un archivo PHP que maneje las rutas.

---

## ✅ Checklist

- [ ] Commit los cambios (nginx_app.conf, Procfile, workflow)
- [ ] Push a GitHub
- [ ] Esperar build de GitHub Actions (2-3 min)
- [ ] Esperar deploy de Heroku (2-3 min)
- [ ] Verificar logs de Heroku
- [ ] Probar URL amigable
- [ ] Verificar que URLs antiguas funcionen

---

¿Listo para hacer el push y probar? 🚀
