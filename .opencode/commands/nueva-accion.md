---
description: Añade una acción a acciones.json siempre con los mismos pasos
---

Quiero añadir esta acción a `acciones.json`: $ARGUMENTS

Sigue estos pasos, en orden, y para después de cada uno si algo no cuadra:

1. Carga la skill `acciones-json` y lee `acciones.json`.
2. Propón el objeto JSON de la acción (nombre, descripción, tipo, filtro…) y explícame cada campo. Si hace falta un tipo que no existe, dímelo y no sigas.
3. Cuando lo apruebe, añádelo al final de la lista sin tocar las demás acciones.
4. Ejecuta `uv run tareas validar`.
5. Crea ficheros de ejemplo en `~/pruebas-tareas` y ejecuta la acción con `--simular`. Enséñame la salida.
6. Propón una línea para `CHANGELOG.md` y un mensaje de commit. No hagas el commit.
