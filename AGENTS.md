# AGENTS.md · cli-tareas

CLI `tareas` para el trabajo diario de Tronk Studios: ejecuta sobre una carpeta
las acciones definidas en `acciones.json` (prompt nuevo, versión de la caché,
pesos, copias, WebP, miniaturas, nombres para la web, vídeos, basura).

## Stack

- Python 3.12, Typer (interfaz), Rich (tablas y colores), Pillow (WebP), platformdirs (carpeta de configuración del usuario), pytest.
- uv para todo: `uv sync`, `uv run tareas …`, `uv run pytest -q`.

## Órdenes del proyecto

| Para… | Orden |
| --- | --- |
| Instalar dependencias | `uv sync` |
| Probar la CLI | `uv run tareas --help` |
| Validar las acciones | `uv run tareas validar` |
| Ver qué haría una acción | `uv run tareas ejecutar NOMBRE ~/pruebas-tareas --simular` |
| Pruebas | `uv run pytest -q` |

## Estructura

- `src/tareas/cli.py`: solo interfaz (Typer, Rich, códigos de salida). No hace trabajo.
- `src/tareas/motor.py`: `Motor.planificar()` (no toca el disco) y `Motor.ejecutar()`.
- `src/tareas/acciones.py`: una clase por tipo (`mover`, `copiar`, `renombrar`, `borrar`, `webp`, `informe`, `crear`, `incrementar`, `comprimir`), registradas en `TIPOS`. Las que trabajan fichero a fichero implementan `planificar()`; las demás redefinen `preparar()`.
- `src/tareas/config.py`: busca (`--config` → `./acciones.json` → el del usuario), lee y valida `acciones.json`; cada error empieza por la ruta del campo.
- `src/tareas/errores.py`: `TareasError` (1), `ErrorUso` (2), `ConfigError` (3), `AccionNoValida`, `AccionNoEncontrada`.

## Normas

- Rutas siempre con `pathlib` y `expanduser()`; nunca concatenando textos.
- Ficheros de texto siempre con `encoding="utf-8"`.
- Nada de `os.system` ni `shell=True`: `shutil` y `Path`.
- Colores solo con Rich; los nombres de fichero se pasan por `rich.markup.escape`.
- Nunca sobrescribir: si el destino existe, la operación se omite y se dice por qué.
- Errores previsibles → excepción propia con mensaje humano, nunca un traceback.
- Un tipo nuevo = clase en `acciones.py` + campos en `config.py` + prueba en `tests/`.
- Una acción nueva = solo `acciones.json` (usa `/nueva-accion`).
- Prueba siempre en `~/pruebas-tareas`, nunca en la carpeta real de la web.
- **No hagas commits ni push**: los hace la persona.
- No leas ni escribas `.env`.
