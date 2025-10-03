//
// Scripts
// 

// Función para inyectar estilos de Bootstrap en iframes del mismo dominio
function injectBootstrapIntoIframes() {
    const iframes = document.querySelectorAll('iframe');
    console.log(`🎨 Intentando inyectar Bootstrap en ${iframes.length} iframe(s)`);
    
    iframes.forEach((iframe, index) => {
        try {
            // Esperar a que el iframe esté completamente cargado
            iframe.onload = function() {
                try {
                    // Intentar acceder al documento del iframe (solo funciona si es el mismo dominio)
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    if (!iframeDoc) {
                        console.warn(`⚠️ No se pudo acceder al documento del iframe ${index + 1} (posiblemente dominio diferente)`);
                        return;
                    }
                    
                    // Verificar si Bootstrap ya está cargado
                    const existingBootstrap = iframeDoc.querySelector('link[href*="bootstrap"]');
                    if (existingBootstrap) {
                        console.log(`✅ Bootstrap ya está en el iframe ${index + 1}`);
                        return;
                    }
                    
                    // Crear y agregar el link de Bootstrap CSS
                    const link = iframeDoc.createElement('link');
                    link.rel = 'stylesheet';
                    link.href = 'https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css';
                    link.integrity = 'sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65';
                    link.crossOrigin = 'anonymous';
                    
                    // Agregar al head del iframe
                    if (iframeDoc.head) {
                        iframeDoc.head.appendChild(link);
                        console.log(`✅ Bootstrap inyectado exitosamente en iframe ${index + 1}`);
                    }
                    
                    // También agregar estilos personalizados para mejorar la visualización
                    const style = iframeDoc.createElement('style');
                    style.textContent = `
                        body {
                            font-family: 'Merriweather', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                            padding: 1rem;
                        }
                    `;
                    if (iframeDoc.head) {
                        iframeDoc.head.appendChild(style);
                    }
                    
                } catch (error) {
                    console.warn(`⚠️ No se pudo inyectar estilos en iframe ${index + 1}:`, error.message);
                    console.info('ℹ️ Esto es normal si el iframe carga contenido de un dominio diferente (CORS)');
                }
            };
            
            // Si el iframe ya está cargado, disparar onload manualmente
            if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
                iframe.onload();
            }
            
        } catch (error) {
            console.warn(`⚠️ Error al procesar iframe ${index + 1}:`, error.message);
        }
    });
}

window.addEventListener('DOMContentLoaded', event => {

    // Navbar shrink function
    var navbarShrink = function () {
        const navbarCollapsible = document.body.querySelector('#mainNav');
        if (!navbarCollapsible) {
            return;
        }
        if (window.scrollY === 0) {
            navbarCollapsible.classList.remove('navbar-shrink')
        } else {
            navbarCollapsible.classList.add('navbar-shrink')
        }

    };

    // Shrink the navbar 
    navbarShrink();

    // Shrink the navbar when page is scrolled
    document.addEventListener('scroll', navbarShrink);

    // Activate Bootstrap scrollspy on the main nav element
    const mainNav = document.body.querySelector('#mainNav');
    if (mainNav) {
        new bootstrap.ScrollSpy(document.body, {
            target: '#mainNav',
            rootMargin: '0px 0px -40%',
        });
    };

    // Collapse responsive navbar when toggler is visible
    const navbarToggler = document.body.querySelector('.navbar-toggler');
    const responsiveNavItems = [].slice.call(
        document.querySelectorAll('#navbarResponsive .nav-link')
    );
    responsiveNavItems.map(function (responsiveNavItem) {
        responsiveNavItem.addEventListener('click', () => {
            if (window.getComputedStyle(navbarToggler).display !== 'none') {
                navbarToggler.click();
            }
        });
    });

    // Activate SimpleLightbox plugin for portfolio items
    new SimpleLightbox({
        elements: '#portfolio a.portfolio-box'
    });


    // String to Slug
    function stringToSlug(str) {
        // Convierte el string a minúsculas y reemplaza caracteres acentuados y diacríticos
        const from = "áäàâãåéëèêíïìîĩóöòôõúüùûñç";
        const to = "aaaaaaeeeeiiiiiooooouuuunc";
        for (let i = 0; i < from.length; i++) {
            str = str.toLowerCase().replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
        }

        // Reemplaza espacios y caracteres no alfanuméricos con guiones
        str = str.replace(/[^a-z0-9]+/g, '-');

        // Elimina guiones repetidos y guiones al principio o al final del slug
        str = str.replace(/^-+|-+$/g, '');

        return str;
    }

    // URL API
    const baseUrl = 'https://api.datoseducativos.cl';
    const projectsUrl = baseUrl + '/projects';
    const homeUrl = baseUrl + '/home';

    // Si la url es la url base
    if (window.location.pathname == '/') {
        // Muestra el spinner solo si existe el elemento
        const loaderProjects = document.getElementById('loader-projects');
        if (loaderProjects) {
            loaderProjects.style.display = 'block';
        }

        // Procesa Datos Home
        fetch(homeUrl)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Error al obtener datos de la API');
            }
        })
        .then(data => {
            // Procesa los datos y genera el HTML (solo si los elementos existen)
            const updateElement = (id, value) => {
                const element = document.getElementById(id);
                if (element) element.innerHTML = value;
            };
            
            updateElement('titulo_principal', data.TITULO_PRINCIPAL);
            updateElement('sub_titulo_principal', data.SUB_TITULO_PRINCIPAL);
            updateElement('titulo_secundario', data.TITULO_SECUNDARIO);
            updateElement('sub_titulo_secundario', data.SUB_TITULO_SECUNDARIO);
            updateElement('titulo_contacto', data.TITULO_CONTACTO);
            updateElement('sub_titulo_contacto', data.SUB_TITULO_CONTACTO);
        })
        .catch(error => {
            console.error('Error al procesar la API:', error);
        })

        // Procesa Proyectos
        fetch(projectsUrl)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Error al obtener datos de la API');
            }
        })
        .then(data => {
            // Procesa los datos y genera el HTML
            const projects = document.getElementById('projects');
            let html_project = '';

            data.forEach(item => {

                // Imagen de proyecto
                if (item.url_imagen != '') {
                    var img = item.url_imagen;
                } else {
                    var img = `assets/img/portfolio/placeholder.jpg`;
                }

                // URL del proyecto: priorizar slug sobre id
                // Formato: /proyecto/slug (sin .html, sin query params)
                let projectUrl;
                if (item.slug && item.slug.trim() !== '') {
                    projectUrl = `/proyecto/${item.slug}`;
                } else {
                    // Fallback para proyectos sin slug
                    projectUrl = `/proyecto.html?id=${item.id}`;
                }


                // Aquí, crea el HTML según los datos recibidos de la API
                html_project += `
                    <!-- Project ${item.proyecto} -->
                    <div class="col-lg-4 col-sm-6">
                        <a class="portfolio-box" href="${projectUrl}" target="_self" title="${item.proyecto}">
                            <img class="img-fluid project-img" src="${img}" alt="${item.proyecto}">
                            <div class="portfolio-box-caption-alt">
                                <div class="project-name">
                                    ${item.proyecto}
                                </div>
                                <div class="project-name">
                                    ${item.anio}
                                </div>
                                <p class="project-persona_a_cargo">
                                    <i>${item.persona_a_cargo}</i>
                                </p>
                            </div>

                            <div class="portfolio-box-caption">
                                <div class="project-category text-white-50">
                                    ${item.tipo}
                                </div>
                                <div class="project-name">
                                    ${item.proyecto} - (${item.anio})
                                </div>
                                <p class="project-description">
                                    ${item.descripcion}
                                </p>
                            </div>
                        </a>
                    </div>
                `;
            });

            // Inserta el HTML generado en el elemento 'projects'
            projects.innerHTML = html_project;
        })
        .catch(error => {
            console.error('Error al procesar la API:', error);
        })
        .finally(() => {
            // Oculta el spinner solo si existe
            const loaderProjects = document.getElementById('loader-projects');
            if (loaderProjects) {
                loaderProjects.style.display = 'none';
            }
        });
    }

    // Detectar si estamos en la página de proyecto
    // Puede ser /proyecto.html o /proyecto/slug
    const isProjectPage = window.location.pathname === '/proyecto.html' || 
                         window.location.pathname.startsWith('/proyecto/');

    if (isProjectPage) {
        // Muestra el spinner
        const loaderTitulo = document.getElementById('loader-titulo');
        const loaderHtml = document.getElementById('loader-html');
        if (loaderTitulo) loaderTitulo.style.display = 'block';
        if (loaderHtml) loaderHtml.style.display = 'block';

        // Get the url parameters
        const urlParams = new URLSearchParams(window.location.search);
        let id = urlParams.get('id');
        let slug = urlParams.get('slug');

        // Si la URL es /proyecto/slug (sin query params), extraer el slug del pathname
        if (!slug && window.location.pathname.startsWith('/proyecto/')) {
            const pathParts = window.location.pathname.split('/');
            // pathParts = ['', 'proyecto', 'slug']
            if (pathParts.length >= 3 && pathParts[2]) {
                slug = pathParts[2];
                console.log('Slug extraído del pathname:', slug);
            }
        }

        // Verificar si viene de una redirección 404 (ruta amigable)
        const sessionSlug = sessionStorage.getItem('projectSlug');
        if (sessionSlug && !slug) {
            slug = sessionSlug;
            sessionStorage.removeItem('projectSlug');
            console.log('Slug extraído de sessionStorage:', slug);
        }

        // Determinar qué endpoint usar
        let projectsUrlId;
        if (slug) {
            // Si hay un slug, usar el endpoint de slug
            projectsUrlId = baseUrl + '/projects/slug/' + slug;
            console.log('🔍 Buscando proyecto por slug:', slug);
            console.log('📡 URL de API:', projectsUrlId);
        } else if (id) {
            // Si hay un id, usar el endpoint de id
            projectsUrlId = baseUrl + '/projects/' + id;
            console.log('🔍 Buscando proyecto por ID:', id);
            console.log('📡 URL de API:', projectsUrlId);
        } else {
            // Si no hay ni id ni slug, mostrar error
            console.error('❌ No se proporcionó ni id ni slug en la URL');
            const loaderTitulo = document.getElementById('loader-titulo');
            const loaderHtml = document.getElementById('loader-html');
            if (loaderTitulo) loaderTitulo.style.display = 'none';
            if (loaderHtml) loaderHtml.style.display = 'none';
            document.getElementById('proyecto_titulo').innerHTML = 'Error: No se proporcionó ID o slug';
            return;
        }

        // Procesa Proyectos
        fetch(projectsUrlId)
        .then(response => {
            console.log('📥 Respuesta de API - Status:', response.status);
            if (response.ok) {
                return response.json();
            } else {
                throw new Error(`Error al obtener datos de la API: ${response.status}`);
            }
        })
        .then(data => {
            console.log('✅ Datos recibidos de la API:', data);
            
            // Verificar si hay un error en la respuesta
            if (data.error) {
                console.error('❌ Error en la respuesta de la API:', data.message || data.error);
                document.getElementById('proyecto_titulo').innerHTML = `Error: ${data.message || data.error}`;
                document.getElementById('proyecto_descripcion').innerHTML = `
                    <p>No se pudo cargar el proyecto con slug "${slug}".</p>
                    <p>Verifica que el slug existe en Google Sheets.</p>
                    <p><a href="/">Volver a la página principal</a></p>
                `;
                const loaderTitulo = document.getElementById('loader-titulo');
                const loaderHtml = document.getElementById('loader-html');
                if (loaderTitulo) loaderTitulo.style.display = 'none';
                if (loaderHtml) loaderHtml.style.display = 'none';
                return;
            }
            
            // Verificar que los datos necesarios existen
            if (!data.proyecto) {
                console.error('❌ La API no devolvió datos válidos:', data);
                document.getElementById('proyecto_titulo').innerHTML = 'Error: Datos inválidos';
                const loaderTitulo = document.getElementById('loader-titulo');
                const loaderHtml = document.getElementById('loader-html');
                if (loaderTitulo) loaderTitulo.style.display = 'none';
                if (loaderHtml) loaderHtml.style.display = 'none';
                return;
            }
            
            // Procesa los datos y genera el HTML
            console.log('📝 Proyecto encontrado:', data.proyecto);
            document.getElementById('proyecto_titulo').innerHTML = `${data.proyecto} - (${data.anio})`;
            document.getElementById('proyecto_descripcion').innerHTML = data.descripcion;
            document.getElementById('proyecto_equipo').innerHTML = data.equipo;

            if (data.ID_proyecto != '') {
                id_proyetco = data.ID_proyecto;
                urlProyecto = baseUrl + `/project/${id_proyetco}/html`;

                // Obtiene el HTML del proyecto
                fetch(urlProyecto)
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        throw new Error('Error al obtener datos de la API');
                    }
                })
                .then(data => {
                    // Procesa los datos y genera el HTML
                    document.getElementById('proyecto_html_raw').innerHTML = data.html;
                    
                    // Inyectar estilos de Bootstrap en todos los iframes
                    setTimeout(() => {
                        injectBootstrapIntoIframes();
                    }, 500); // Esperar un poco para que los iframes se carguen
                })
                .catch(error => {
                    console.error('Error al procesar la API:', error);
                })
                .finally(() => {
                    // Oculta el spinner
                    const loaderTitulo = document.getElementById('loader-titulo');
                    const loaderHtml = document.getElementById('loader-html');
                    if (loaderTitulo) loaderTitulo.style.display = 'none';
                    if (loaderHtml) loaderHtml.style.display = 'none';
                });

            }else{
                document.getElementById('proyecto_html_raw').innerHTML = '';
            }

        })
        .catch(error => {
            console.error('❌ Error al procesar la API:', error);
            document.getElementById('proyecto_titulo').innerHTML = 'Error al cargar el proyecto';
            document.getElementById('proyecto_descripcion').innerHTML = `
                <p>Hubo un error al cargar los datos del proyecto.</p>
                <p>Error: ${error.message}</p>
                <p><a href="/">Volver a la página principal</a></p>
            `;
        })
        .finally(() => {
            // Oculta el spinner
            const loaderTitulo = document.getElementById('loader-titulo');
            if (loaderTitulo) loaderTitulo.style.display = 'none';
        });
        
    }
    
});
