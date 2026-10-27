# Prompts clave

Los prompts que decidieron algo importante, con lo que salió y lo que hicimos
con la respuesta. Misma plantilla que en `tronkstudios.github.io/docs/prompts`.

## 1. Arrancar el proyecto

- **Fecha:** 27/10/2026
- **Herramienta:** Claude Code
- **Commits:** de «Proyecto uv con Typer…» a «README, CHANGELOG 0.1.0…»

### Qué necesitábamos
Montar la CLI del proyecto del curso, pero útil para Tronk Studios.

### El prompt
```
(el enunciado del proyecto del curso)
crea el repo, quiero que el cli me sirva para hacer cosas de tronkstudios
```

### Qué hicimos con la respuesta
- Aceptado: estructura `cli` / `config` / `motor` / `acciones` / `errores`,
  tipos `mover`, `copiar`, `renombrar`, `borrar` y `webp`, y las acciones de
  capturas, miniaturas, nombres web, originales, demos y basura.
- Cambiado: _(rellenar)_
- Descartado y por qué: _(rellenar)_

## 2. Que sirva en el día a día de la web

- **Fecha:** 27/10/2026
- **Herramienta:** Claude Code
- **Commits:** de «Tipos para la web…» a «Documentación de los tipos nuevos…»

### Qué necesitábamos
Las primeras acciones solo servían para imágenes. Queríamos lo que repetimos
cada semana con la web.

### El prompt
```
pero no podemos hacer que sea algo que me ayude en un futuro?
pues hazlo
```

### Qué hicimos con la respuesta
- Aceptado: tipos `crear`, `incrementar`, `informe` y `comprimir`, y las
  acciones `nuevo-prompt`, `subir-cache`, `revisar-pesos` y `copia-seguridad`.
  Usar el `acciones.json` del usuario si no hay uno en la carpeta.
- Cambiado: _(rellenar)_
- Descartado y por qué: la lista larga de ideas (sprites, redes, traducir…):
  no las repetimos lo bastante como para que compensen.

## 3. El fallo de Windows

- **Fecha:** 27/10/2026
- **Herramienta:** Claude Code + GitHub Actions
- **Commit:** «Windows: no reventar en consolas cp1252…»

### Qué necesitábamos
GitHub Actions falló en `windows-latest`: `tareas validar` reventaba con
`UnicodeEncodeError` al escribir ✓ en una consola cp1252.

### Qué hicimos con la respuesta
- Aceptado: reproducirlo en Linux con `PYTHONIOENCODING=cp1252`, arreglarlo
  con `reconfigure(errors="replace")` y dejar una prueba que lo reproduce.

## 4. Guía del código, proceso y v1.0

- **Fecha:** 27/10/2026
- **Herramienta:** Claude Code
- **PR:** ramas `docs/guia-y-proceso` y `release/v1.0.0`

### El prompt
```
haz todo menos la ia
```

### Qué hicimos con la respuesta
- Aceptado: `docs/guia-del-codigo.md` para poder explicar cada fichero y
  cada prueba, plantilla de PR, trabajo en ramas y PR, y release v1.0.0.
