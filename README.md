# cli-tareas

`tareas` es una CLI para el trabajo diario de **Tronk Studios**. Lo que
antes hacías a mano y siempre igual (crear el prompt nuevo, subir la versión
de la caché, comprobar que nada pesa demasiado, preparar capturas, hacer una
copia) pasa a ser una orden. Las acciones se describen en `acciones.json`, no
en el código: si mañana cambia algo, cambias un número en el JSON.

## Un día normal con la web

```bash
cd ~/tronkstudios.github.io

tareas ejecutar nuevo-prompt -t "Tronker en Discord"   # docs/prompts/19-tronker-en-discord.md
# … trabajas en la web …
tareas ejecutar revisar-pesos                          # ¿algo pesa más de 200 KB?
tareas ejecutar subir-cache                            # sw.js: CACHE_VERSION 6 → 7
tareas ejecutar copia-seguridad                        # ~/Copias/tronkstudios/…zip
```

```text
tareas ejecutar capturas-webp ~/Capturas --simular
SIMULACIÓN · capturas-webp (webp) en /home/jose/Capturas
  → Captura Física [1].png → /home/jose/Capturas/webp/captura-fisica-1.webp
1 operaciones, 0 omitidas.
Simulación: no se ha tocado nada.
```

## Instalación

Necesitas [uv](https://docs.astral.sh/uv/getting-started/installation/). Él se encarga de Python 3.12.

```bash
uv tool install git+https://github.com/tronkstudios/cli-tareas
# o, sin uv:
pipx install git+https://github.com/tronkstudios/cli-tareas

tareas --help
```

Desinstalar: `uv tool uninstall tareas`.

Para desarrollar (cada cambio se nota al momento):

```bash
git clone https://github.com/tronkstudios/cli-tareas
cd cli-tareas
uv tool install --editable .
```

## Órdenes

| Orden | Qué hace |
| --- | --- |
| `tareas --help` | Ayuda general. Cada orden tiene la suya: `tareas ejecutar --help`. |
| `tareas version` | Versión instalada. |
| `tareas listar [CARPETA] [--json]` | Tabla con nombre, tipo, tamaño y fecha. Por defecto, la carpeta actual. |
| `tareas acciones [--json]` | Las acciones de `acciones.json`. |
| `tareas validar` | Comprueba `acciones.json` y dice qué campo falla. |
| `tareas ejecutar NOMBRE [CARPETA] --simular` | Enseña qué haría, sin tocar nada. |
| `tareas ejecutar NOMBRE [CARPETA] --si` | La ejecuta sin preguntar (para scripts). |
| `tareas ejecutar NOMBRE --texto "…"` | Título para las acciones que crean ficheros (`-t`). |
| `tareas --config RUTA …` | Usa otro fichero de acciones (o la variable `TAREAS_CONFIG`). |

**Códigos de salida:** 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.

**¿Qué `acciones.json` usa?** El de `--config` (o `TAREAS_CONFIG`); si no
lo das, el de la carpeta actual; y si ahí no hay, **el de tu usuario**. Para
usar tus acciones desde cualquier carpeta (por ejemplo, la de la web), copia
el tuyo allí una vez:

| Sistema | Dónde va |
| --- | --- |
| Linux | `~/.config/tareas/acciones.json` |
| macOS | `~/Library/Application Support/tareas/acciones.json` |
| Windows | `%LOCALAPPDATA%\tareas\tareas\acciones.json` |

```bash
mkdir -p ~/.config/tareas && cp acciones.json ~/.config/tareas/   # Linux
```

## Las acciones de Tronk Studios

Las cuatro primeras se lanzan desde la carpeta de la web:

| Acción | Tipo | Qué hace |
| --- | --- | --- |
| `nuevo-prompt` | crear | `-t "Título"` → `docs/prompts/19-titulo.md` desde `plantilla.md`, con título y fecha puestos. |
| `subir-cache` | incrementar | Suma 1 a `CACHE_VERSION` en `sw.js`. |
| `revisar-pesos` | informe | Lista imágenes y vídeos de más de 200 KB, de mayor a menor. No toca nada. |
| `copia-seguridad` | comprimir | `.zip` de la carpeta con fecha y hora en `~/Copias/tronkstudios/`, sin `.git`. |
| `capturas-webp` | webp | PNG/JPG → WebP de 1280 px como máximo, en `webp/`. |
| `miniaturas-juegos` | webp | Miniaturas de 480 px para las tarjetas, en `mini/` (como `img/juegos/mini`). |
| `nombres-web` | renombrar | `Captura Tronk Fight.PNG` → `captura-tronk-fight.png`. |
| `archivar-originales` | mover | Saca PNG/JPG/PSD a `originales/` para que no acaben en el repo. |
| `ordenar-demos` | mover | Lleva `.mp4` y `.webm` a `video/`. |
| `limpiar-basura` | borrar | Borra `.DS_Store`, `Thumbs.db`, `.tmp` y `.bak` en todo el proyecto, sin entrar en `.git`. Pide confirmación. |

Flujo típico para una captura nueva de un juego:

```bash
cd ~/Capturas
tareas ejecutar capturas-webp --simular      # mira qué hará
tareas ejecutar capturas-webp                # captura → webp/
tareas ejecutar miniaturas-juegos webp       # webp/ → webp/mini/
tareas ejecutar archivar-originales          # los PNG, fuera
```

Y copias `webp/*.webp` a `img/juegos/` y `webp/mini/*.webp` a `img/juegos/mini/` de la web.

## acciones.json

```json
{
  "version": 1,
  "acciones": [
    {
      "nombre": "miniaturas-juegos",
      "descripcion": "Crea las miniaturas de 480 px de las tarjetas en mini/",
      "tipo": "webp",
      "filtro": { "extensiones": [".png", ".jpg", ".jpeg", ".webp"] },
      "destino": "mini",
      "ancho_max": 480,
      "calidad": 75
    }
  ]
}
```

| Campo | Para qué |
| --- | --- |
| `version` | Versión del esquema. Ahora, `1`. |
| `nombre` | Lo que se teclea. Minúsculas, números y guiones; único. |
| `descripcion` | Lo que enseña `tareas acciones`. |
| `tipo` | `mover`, `copiar`, `renombrar`, `borrar`, `webp`, `informe`, `crear`, `incrementar` o `comprimir`. |
| `origen` | Carpeta por defecto (admite `~`). La CARPETA de la orden manda sobre ella; si no hay ninguna, la actual. |
| `destino` | `mover`/`copiar` (obligatorio) y `webp` (opcional). Si es relativo, va dentro de la carpeta de trabajo. |
| `plantilla` | `renombrar`: `{fecha:%Y-%m-%d}`, `{n:03}`, `{ext}`, `{nombre}` y `{slug}` (nombre sin tildes, espacios ni mayúsculas). |
| `ancho_max`, `calidad` | `webp`: ancho máximo en píxeles y calidad 1-100 (80 por defecto). |
| `filtro` | `extensiones` (`[".png"]`), `patron` (expresión regular sobre el nombre), `mas_antiguo_que_dias`, `mas_grande_que_kb`, `recursivo`. |
| `modelo`, `nombre_fichero`, `reemplazar` | `crear`: fichero modelo, nombre del nuevo (`{n:02}` = número siguiente, `{slug}`, `{fecha}`) y textos a cambiar (`{texto}` = lo que pasas con `-t`). |
| `fichero`, `patron` | `incrementar`: dónde está el número y una expresión regular con el número entre paréntesis. |
| `nombre_fichero` | `comprimir`: por defecto `{carpeta}-{fecha:%Y-%m-%d_%H%M}.zip`. |
| `confirmar` | Pregunta antes de actuar salvo con `--si`. En `borrar` es `true` si no se pone. |

Reglas de seguridad: nunca se sobrescribe un fichero (se omite y se dice
por qué), los ficheros ocultos solo se eligen si el filtro tiene `patron`, y
en modo recursivo no se entra en carpetas ocultas como `.git`.

Añadir una acción no exige tocar el código: edítala en `acciones.json` y
comprueba con `tareas validar`. El porqué está en
[docs/adr/0001-configuracion-externa.md](docs/adr/0001-configuracion-externa.md).

## Estructura

```text
src/tareas/
├── cli.py       # interfaz Typer: órdenes, opciones, salida y códigos de salida
├── config.py    # leer y VALIDAR acciones.json
├── motor.py     # Motor: planificar (sin tocar nada) y ejecutar
├── acciones.py  # una clase por tipo: mover, copiar, renombrar, borrar, webp, informe, crear, incrementar, comprimir
└── errores.py   # TareasError, ErrorUso, ConfigError, AccionNoValida, AccionNoEncontrada
```

## Pruebas

```bash
uv run pytest -q
```

GitHub Actions las ejecuta en Ubuntu, Windows y macOS en cada push.

## Trabajar con OpenCode

- `opencode.json`: permisos (edita y lanza órdenes preguntando; nunca `git commit`, `git push`, `rm` ni leer `.env`).
- `AGENTS.md`: stack, órdenes y normas del proyecto.
- `.opencode/skills/acciones-json/`: reglas del esquema.
- `/nueva-accion <qué quieres>`: añade una acción siempre igual.
- `@revisor`: revisor de solo lectura antes de cada commit.
