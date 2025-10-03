'use strict';
const fs = require('fs');
const upath = require('upath');

const srcPath = upath.resolve(upath.dirname(__filename), '../src/404.html');
const destPath = upath.resolve(upath.dirname(__filename), '../dist/404.html');

// Copiar 404.html a dist
fs.copyFile(srcPath, destPath, (err) => {
    if (err) {
        console.error('Error al copiar 404.html:', err);
    } else {
        console.log('404.html copiado exitosamente a dist/');
    }
});
