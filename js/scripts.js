/*!
* Start Bootstrap - Creative v7.0.7 (https://startbootstrap.com/theme/creative)
* Copyright 2013-2025 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-creative/blob/master/LICENSE)
*/
//
// Scripts
// 

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
        // Muestra el spinner
        document.getElementById('loader-projects').style.display = 'block';

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
            // Procesa los datos y genera el HTML
            document.getElementById('titulo_principal').innerHTML = data.TITULO_PRINCIPAL;
            document.getElementById('sub_titulo_principal').innerHTML = data.SUB_TITULO_PRINCIPAL;
            document.getElementById('titulo_secundario').innerHTML = data.TITULO_SECUNDARIO;
            document.getElementById('sub_titulo_secundario').innerHTML = data.SUB_TITULO_SECUNDARIO;
            document.getElementById('titulo_contacto').innerHTML = data.TITULO_CONTACTO;
            document.getElementById('sub_titulo_contacto').innerHTML = data.SUB_TITULO_CONTACTO;
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


                // Aquí, crea el HTML según los datos recibidos de la API
                html_project += `
                    <!-- Project ${item.proyecto} -->
                    <div class="col-lg-4 col-sm-6">
                        <a class="portfolio-box" href="/proyecto.html?id=${item.id}" target="_self" title="${item.proyecto}">
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
            // Oculta el spinner
            document.getElementById('loader-projects').style.display = 'none';
        });
    }

    if (window.location.pathname == '/proyecto.html') {
        // Muestra el spinner
        document.getElementById('loader-titulo').style.display = 'block';
        document.getElementById('loader-html').style.display = 'block';


        // Get the url parameters
        const urlParams = new URLSearchParams(window.location.search);
        const id = urlParams.get('id');

        const projectsUrlId = baseUrl + '/projects/' + id;

        // Procesa Proyectos
        fetch(projectsUrlId)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Error al obtener datos de la API');
            }
        })
        .then(data => {
            // Procesa los datos y genera el HTML
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
                })
                .catch(error => {
                    console.error('Error al procesar la API:', error);
                })
                .finally(() => {
                    // Oculta el spinner
                    document.getElementById('loader-titulo').style.display = 'none';
                    document.getElementById('loader-html').style.display = 'none';
                });

            }else{
                document.getElementById('proyecto_html_raw').innerHTML = '';
            }

        })
        .catch(error => {
            console.error('Error al procesar la API:', error);
        })
        .finally(() => {
            // Oculta el spinner
            document.getElementById('loader-titulo').style.display = 'none';
        });
        
    }
    
});
