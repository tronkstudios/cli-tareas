# Changelog

## 0.1.0 · 27 de octubre de 2026

- Órdenes `version`, `listar` (tabla o `--json`), `acciones`, `validar` y `ejecutar` (`--simular`, `--si`).
- Opción global `--config` (o variable `TAREAS_CONFIG`).
- Tipos de acción: `mover`, `copiar`, `renombrar` (con `{slug}`), `borrar` y `webp`.
- Tipos para la web: `crear` (fichero desde un modelo con número siguiente), `incrementar` (sube un número dentro de un fichero), `informe` (solo lista) y `comprimir` (copia .zip con fecha).
- Opción `--texto` en `ejecutar` y filtro `mas_grande_que_kb`.
- Si no hay `./acciones.json`, se usa el de la carpeta de configuración del usuario.
- 10 acciones de Tronk Studios en `acciones.json`: `nuevo-prompt`, `subir-cache`, `revisar-pesos`, `copia-seguridad`, `capturas-webp`, `miniaturas-juegos`, `nombres-web`, `archivar-originales`, `ordenar-demos` y `limpiar-basura`.
- Códigos de salida: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
