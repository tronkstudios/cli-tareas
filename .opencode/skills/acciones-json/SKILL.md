---
name: acciones-json
description: Reglas del esquema de acciones.json de tareas. Cárgala siempre que vayas a leer, crear o cambiar una acción.
---

# Esquema de acciones.json (versión 1)

```json
{ "version": 1, "acciones": [ { ... } ] }
```

## Campos de toda acción

| Campo | Obligatorio | Regla |
| --- | --- | --- |
| `nombre` | sí | minúsculas, números y guiones (`miniaturas-juegos`); único |
| `descripcion` | sí | una frase que diga qué hace |
| `tipo` | sí | `mover`, `copiar`, `renombrar`, `borrar` o `webp` |
| `origen` | no | carpeta por defecto; admite `~`. La CARPETA de la orden manda sobre ella |
| `filtro` | no | ver abajo; sin filtro le afectan todos los ficheros no ocultos |
| `confirmar` | no | `true`/`false`. En `borrar` vale `true` si no se pone |

## Campos por tipo

- `mover`, `copiar`: `destino` (obligatorio). Si es relativo, va dentro de la carpeta de trabajo.
- `renombrar`: `plantilla` (obligatorio) con `{fecha:%Y-%m-%d}`, `{n:03}`, `{ext}`, `{nombre}`, `{slug}`. Sin `/` ni `\`.
- `borrar`: nada más.
- `webp`: `destino` (opcional), `ancho_max` (1-20000), `calidad` (1-100, por defecto 80).

## filtro

- `extensiones`: lista que empieza por punto: `[".png", ".jpg"]` (no distingue mayúsculas).
- `patron`: expresión regular sobre el nombre (en JSON, `\\.` para un punto).
- `mas_antiguo_que_dias`: número >= 0.
- `recursivo`: `true` para entrar en subcarpetas (nunca entra en carpetas ocultas como `.git`).
- Los ficheros ocultos solo se eligen si hay `patron`.

## Al terminar

1. `uv run tareas validar` debe decir ✓.
2. `uv run tareas ejecutar NOMBRE ~/pruebas-tareas --simular` debe enseñar lo esperado.
3. Las acciones destructivas (`borrar`, o `mover` fuera del proyecto) llevan `"confirmar": true`.
