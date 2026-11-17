# Changelog

## Sin publicar

### Documentación
- Prueba de la capa de IA con el modelo del centro (`Qwen38-DualSpark-low`):
  `comprobar-ia` y las tres acciones de IA funcionan. Resultados en
  `docs/prompts.md`, apartado 6.

## 1.1.1 · 16 de noviembre de 2026

### Cambiado
- `revisar-pesos` solo mira imágenes (200 KB) y la nueva `revisar-videos`
  mira los vídeos con el límite de la web (300 KB). Al usar la CLI sobre la
  web, avisaba de un vídeo que ya cumplía. Solo cambia `acciones.json`.

## 1.1.0 · 16 de noviembre de 2026 · Capa de IA

### Añadido
- Tipo de acción `ia`: manda ficheros de texto, los últimos commits o los
  cambios sin commitear a un modelo con las instrucciones escritas en
  `acciones.json`, y guarda la respuesta (o la enseña en pantalla).
- Acciones `borrador-changelog`, `mensaje-commit` y `resumir-documentos`.
- `tareas comprobar-ia` y columna «IA» en `tareas acciones`.
- `ia.py`: `ProveedorIA` abstracto y `ProveedorOpenAI` (API compatible con
  OpenAI, sin SDK), configurado con `TAREAS_IA_*` o un `.env`
  (`.env.example` documentado). Admite el certificado propio del centro
  (`TAREAS_IA_CA`) sin desactivar la verificación.
- ADR 0002 sobre el proveedor de IA.

### Modo sin red
- Sin configuración, sin red, con la clave mal o con el modelo caído (503),
  la acción lo dice en una línea y sale con código 1; el resto de acciones
  no carga ni necesita la IA. `--simular` nunca llama al modelo.

## 1.0.0 · 27 de octubre de 2026

Primera versión estable: todo lo que pide el proyecto salvo la capa de IA,
que llegará en la 1.1.

### Arreglado
- Windows: la CLI ya no se cierra con `UnicodeEncodeError` al escribir ✓ o →
  en consolas cp1252 (lo detectó GitHub Actions).

### Añadido
- `docs/guia-del-codigo.md`: cómo viaja una orden, qué hace cada fichero y
  qué demuestra cada prueba.
- Plantilla de PR y prompts clave en `docs/prompts.md`.
- 27 pruebas que pasan en Ubuntu, Windows y macOS.

## 0.1.0 · 27 de octubre de 2026

- Órdenes `version`, `listar` (tabla o `--json`), `acciones`, `validar` y `ejecutar` (`--simular`, `--si`).
- Opción global `--config` (o variable `TAREAS_CONFIG`).
- Tipos de acción: `mover`, `copiar`, `renombrar` (con `{slug}`), `borrar` y `webp`.
- Tipos para la web: `crear` (fichero desde un modelo con número siguiente), `incrementar` (sube un número dentro de un fichero), `informe` (solo lista) y `comprimir` (copia .zip con fecha).
- Opción `--texto` en `ejecutar` y filtro `mas_grande_que_kb`.
- Si no hay `./acciones.json`, se usa el de la carpeta de configuración del usuario.
- 10 acciones de Tronk Studios en `acciones.json`: `nuevo-prompt`, `subir-cache`, `revisar-pesos`, `copia-seguridad`, `capturas-webp`, `miniaturas-juegos`, `nombres-web`, `archivar-originales`, `ordenar-demos` y `limpiar-basura`.
- Códigos de salida: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
