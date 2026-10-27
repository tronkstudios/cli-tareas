# Spec de `tareas`

1. **Para quién:** para mí, desarrollando la web y los minijuegos de Tronk Studios.
2. **Problema:** las tareas repetidas de la web (prompt nuevo, subir la caché, revisar pesos, copias, preparar capturas) son lentas a mano y se me olvidan pasos.
3. **Qué hace:** ejecuta acciones de `acciones.json` sobre una carpeta: crear desde plantilla, subir un número, informar, comprimir, WebP, renombrar, mover y borrar.
4. **Órdenes:** `version`, `listar`, `acciones`, `validar`, `ejecutar NOMBRE [CARPETA] [--simular] [--si]` y la opción global `--config`.
5. **Siempre** se puede ver antes qué hará (`--simular`), y lo que borra pide confirmación.
6. **Nunca** sobrescribe un fichero que ya existe: lo omite y lo dice.
7. **No hará:** subir nada a GitHub ni hacer commits, ni tocar `.git`; en la web solo cambia lo que dice una acción (p. ej., el número de `sw.js`).
8. **Añadir una acción** = editar `acciones.json`, sin tocar el código.
9. **Funciona** en Linux, Windows y macOS (Python 3.12 + Typer + uv).
10. **Semana 3:** acciones con IA (p. ej., textos alternativos de las capturas) y modo sin red.
