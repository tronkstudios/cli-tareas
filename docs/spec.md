# Spec de `tareas`

1. **Para quién:** para mí, desarrollando la web y los minijuegos de Tronk Studios.
2. **Problema:** preparar capturas, miniaturas y vídeos para la web a mano es lento y se me olvidan pasos (WebP, ancho, nombres sin tildes, no subir los PNG originales).
3. **Qué hace:** ejecuta acciones definidas en `acciones.json` sobre una carpeta: convertir a WebP, crear miniaturas, renombrar para la web, mover y borrar basura.
4. **Órdenes:** `version`, `listar`, `acciones`, `validar`, `ejecutar NOMBRE [CARPETA] [--simular] [--si]` y la opción global `--config`.
5. **Siempre** se puede ver antes qué hará (`--simular`), y lo que borra pide confirmación.
6. **Nunca** sobrescribe un fichero que ya existe: lo omite y lo dice.
7. **No hará:** subir nada a GitHub ni hacer commits, editar HTML/CSS/JS de la web ni tocar `.git`.
8. **Añadir una acción** = editar `acciones.json`, sin tocar el código.
9. **Funciona** en Linux, Windows y macOS (Python 3.12 + Typer + uv).
10. **Semana 3:** acciones con IA (p. ej., textos alternativos de las capturas) y modo sin red.
