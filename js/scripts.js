/*!
* Start Bootstrap - Creative v7.0.7 (https://startbootstrap.com/theme/creative)
* Copyright 2013-2023 Start Bootstrap
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

    // URL de la API que deseas utilizar
    const apiUrl = 'https://datos-analitca-educativa-84942f17b419.herokuapp.com/dae/projects';

    // Realiza la llamada a la API
    fetch(apiUrl)
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
            const projects_modals = document.getElementById('projects-modals');
            let html_project = '';
            let html_project_modal = '';

            data.forEach(item => {

                // Random number between 1 and 3
                const random = Math.floor(Math.random() * 6) + 1;

                // Aquí, crea el HTML según los datos recibidos de la API
                
                html_project += `
                    <!-- Project ${item.proyecto} -->
                    <div class="col-lg-4 col-sm-6">
                        <a class="portfolio-box" href="/proyecto.html?id=${random}" target="_blank" title="${item.proyecto}">
                            <img class="img-fluid" src="assets/img/portfolio/thumbnails/${random}.jpg" alt="${item.proyecto}">
                            <div class="portfolio-box-caption">
                                <div class="project-category text-white-50">
                                    ${item.tipo}
                                </div>
                                <div class="project-name">
                                    ${item.proyecto}
                                </div>
                            </div>
                        </a>
                    </div>

                `;

                html_project_modal += `
                    <!-- Modal Project ${item.proyecto} -->
                    
                `;
            });

            // Inserta el HTML generado en el elemento 'projects'
            projects.innerHTML = html_project;
            projects_modals.innerHTML = html_project_modal;
        })
        .catch(error => {
            console.error('Error al procesar la API:', error);
        });

});
