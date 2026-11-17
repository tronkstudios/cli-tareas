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

## 5. Capa de IA

- **Fecha:** 10-16/11/2026
- **Herramienta:** Claude Code (OpenCode no pudo usarse, ver abajo)
- **PR:** rama `feature/capa-ia`

### Qué necesitábamos
Acciones con IA, la clave fuera del repo y que sin red todo siga funcionando.

### Qué pasó con OpenCode
OpenCode «se quedaba pensando». Al depurarlo vimos que el servidor del centro
usa un certificado propio (`curl: self-signed certificate in certificate
chain`, solucionado con `NODE_EXTRA_CA_CERTS`) y que después los modelos
devolvían `503 No server is available` (los `Qwen38-DualSpark-*`) o no
respondían en 40 s (los `Thinking`). Como no avanzaba, la capa de IA se hizo
con Claude Code.

### El prompt
```
hazme tú todo lo que falta del CLI
```

### Qué hicimos con la respuesta
- Aceptado: `ProveedorIA` abstracto con `urllib` (ADR 0002), tipo `ia` con
  las instrucciones en `acciones.json`, `comprobar-ia`, `TAREAS_IA_CA` para el
  certificado del centro, mensajes de una línea para 401/404/503/timeout y
  pruebas con un servidor local de mentira.
- Aprendido de los errores reales: los 503 y el certificado propio salen en
  los mensajes de la CLI porque fueron justo los problemas que tuvimos.
- Cambiado: _(rellenar)_
- Probado contra el servidor del centro el 17/11/2026 (ver el apartado 6).

## 6. Prueba con el modelo del centro

- **Fecha:** 17/11/2026
- **Herramienta:** `tareas` 1.1.1 con `Qwen38-DualSpark-low` (servidor del centro)

### Qué necesitábamos
Comprobar que la capa de IA funciona con los modelos del centro, no solo
con el servidor de mentira de las pruebas.

### Cómo se configuró
`~/.config/tareas/.env` (fuera del repo, con permisos 600) con
`TAREAS_IA_URL`, `TAREAS_IA_MODELO`, `TAREAS_IA_CLAVE` (la misma que usa
OpenCode) y `TAREAS_IA_CA` apuntando al certificado del centro.

Errores que salieron por el camino y que la CLI explicó en una línea:
- `El servidor de IA rechaza la clave (HTTP 403)`: la clave se había
  guardado vacía.

### Resultado (sobre una copia de la web en `~/pruebas-tareas`)
- `tareas comprobar-ia` → `✓ El modelo responde: OK`.
- `borrador-changelog` (30 commits, 4267 caracteres) → un CHANGELOG con
  «Añadido», «Cambiado» y «Arreglado», escrito para quien visita la web y sin
  inventar nada que no estuviera en los commits.
- `mensaje-commit` → `README: añade línea en blanco al final del archivo`,
  que era justo el cambio.
- `resumir-documentos` (prompts 18 y 19) → dos resúmenes de 5 viñetas con
  qué se necesitaba, qué se decidió y qué quedaba pendiente.

### Qué hicimos con la respuesta
- Aceptado: las instrucciones de las tres acciones se quedan como están.
