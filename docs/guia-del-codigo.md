# Guía del código

Para poder explicar cualquier parte de `tareas` en la defensa. Léela con el
código abierto al lado.

## El viaje de una orden

`tareas ejecutar subir-cache --simular`:

1. **`cli.py` → `ejecutar()`**: Typer ha leído `subir-cache` y `--simular`.
2. **`config.py` → `buscar_config()`** decide qué `acciones.json` usar
   (`--config` → `./acciones.json` → el de tu usuario) y
   **`Configuracion.desde_fichero()`** lo lee y lo **valida**. Si algo falla,
   lanza `ConfigError` con la lista de errores.
3. **`Configuracion.buscar("subir-cache")`** devuelve el objeto
   `AccionIncrementar` (lo creó la fábrica `Accion.desde_dict()`).
4. **`motor.py` → `Motor.planificar()`** comprueba la carpeta y llama a
   `accion.preparar()`, que devuelve una lista de `Operacion`. **No toca el disco.**
5. **`cli.py` → `_mostrar_plan()`** enseña el plan. Con `--simular` acaba aquí.
6. Sin `--simular`: si la acción tiene `confirmar`, pregunta. Después,
   **`Motor.ejecutar()`** llama a `accion.aplicar(op)` para cada operación.
   Si una falla, apunta el fallo y sigue con las demás.
7. **Código de salida:** 0 si todo fue bien, 1 si alguna operación falló.

## Cada fichero

| Fichero | Su único trabajo | Qué preguntar(te) |
| --- | --- | --- |
| `cli.py` | Hablar con la persona: órdenes, opciones, tablas, colores y códigos de salida. | ¿Por qué no hay lógica de ficheros aquí? Para poder probar el motor sin Typer y cambiar la interfaz sin romperlo. |
| `config.py` | Desconfiar del JSON: `validar()` devuelve **todos** los errores con la ruta del campo (`acciones[1].filtro.extensiones`). | ¿Por qué no basta con `json.loads`? Porque un JSON bien escrito puede tener campos que faltan o valores absurdos. |
| `motor.py` | Separar **qué** se haría (`Plan`) de **hacerlo** (`Resultado`). | ¿Por qué planificar primero? Así `--simular` enseña exactamente lo que luego se ejecuta. |
| `acciones.py` | Una clase por tipo. Todas heredan de `Accion`. | ¿Por qué `desde_dict` es `@staticmethod`? Es una **fábrica**: mira `tipo` y crea la subclase adecuada sin que nadie tenga que conocerlas. |
| `errores.py` | Excepciones propias, cada una con su `codigo_salida`. | ¿Por qué propias? Para distinguir «el usuario se equivocó» (mensaje y código) de «hay un bug» (traceback). |

### Ideas que salen en `acciones.py`

- **Herencia y polimorfismo.** El motor solo llama a `preparar()` y
  `aplicar()`. Cada tipo los hace a su manera. Añadir un tipo no cambia el motor.
- **`_argumentos()`** convierte el JSON en los argumentos del constructor.
  Cada subclase añade sus campos con `{**super()._argumentos(datos), ...}`.
- **`@dataclass(frozen=True)`**: una acción no cambia después de crearse.
- **`ClassVar`** (`tipo`, `solo_lectura`): es del tipo, no de cada acción.
- **`planificar()` vs `preparar()`**: los tipos que trabajan fichero a fichero
  (mover, renombrar…) solo implementan `planificar(ficheros)`. Los que no
  (crear, incrementar, comprimir) redefinen `preparar()`.
- **Nunca sobrescribir**: si el destino existe, la operación sale «omitida»
  con el motivo. En `aplicar()` se vuelve a comprobar, por si apareció entre
  el plan y la ejecución. `crear` abre con modo `"x"`, que falla si existe.
- **`assert`**: comprueba cosas que *nunca* deberían pasar si el código está
  bien (p. ej., aplicar una operación omitida). No es para errores del usuario.
- **Multiplataforma**: `pathlib`, `expanduser()`, `encoding="utf-8"`,
  `shutil` en vez de `os.system`, y `newline=""` para no cambiar los saltos
  de línea CRLF/LF al reescribir `sw.js`.

### Ideas que salen en `cli.py`

- **`_sin_traceback()`** es un *context manager*: todo lo que va dentro de
  `with _sin_traceback():` que lance un `TareasError` se convierte en un
  mensaje en rojo por **stderr** y `typer.Exit(codigo)`.
- **`escape()`**: un fichero llamado `foto [1].png` se vería mal (Rich
  interpreta `[...]` como estilo) si no se escapa.
- **`sys.stdin.isatty()`**: si no hay nadie para responder (un script) y la
  acción pide confirmación, se niega a borrar y pide `--si`.
- **`reconfigure(errors="replace")`**: en consolas de Windows cp1252, ✓ y →
  hacían saltar un error. Lo encontró GitHub Actions.

## Cada prueba y qué demuestra

`uv run pytest -q`. `tmp_path` es una carpeta temporal nueva para cada
prueba: nunca se tocan ficheros reales.

### `test_config.py`

| Prueba | Qué comprueba la aserción |
| --- | --- |
| `test_el_acciones_json_del_repo_es_valido` | Nuestro propio `acciones.json` se carga y tiene al menos 5 acciones. |
| `test_dice_que_campo_falla` | A un `mover` sin `destino` le sale **exactamente un** error, y nombra el campo. |
| `test_nombres_repetidos_y_tipo_desconocido` | Detecta dos acciones con el mismo nombre y un `tipo` que no existe. |
| `test_json_roto_da_config_error_con_linea` | Un JSON cortado lanza `ConfigError` diciendo la línea. |
| `test_fichero_que_no_existe` | Sin fichero: `ConfigError` «No encuentro». |
| `test_accion_que_no_existe` | Pedir una acción que no está lanza `AccionNoEncontrada` y lista las que hay. |
| `test_plantilla_con_variable_desconocida` | `{fechas}` (con s) en una plantilla se detecta al validar, no al ejecutar. |

### `test_acciones.py`

| Prueba | Qué comprueba la aserción |
| --- | --- |
| `test_slug_quita_tildes_espacios_y_mayusculas` | `Captura Física (2)` → `captura-fisica-2`. Si no queda nada, `fichero`. |
| `test_simular_no_toca_nada` | El plan encuentra `a.pdf` (aunque el filtro diga `.PDF`), pero el fichero sigue en su sitio y la carpeta destino no se ha creado. |
| `test_mover_no_sobrescribe` | Si el destino ya existe, la operación queda omitida y el fichero viejo conserva su contenido. |
| `test_renombrar_con_slug` | Renombra a `captura-tronk-fight.png` y **no** toca `.DS_Store` (oculto). |
| `test_borrar_recursivo_no_entra_en_git` | `borrar` pide confirmación por defecto; borra `sub/b.tmp` pero no `.git/a.tmp`. |
| `test_webp_reduce_el_ancho` | Una imagen de 2000×1000 sale en WebP a 480×240 (mantiene la proporción). |
| `test_webp_con_fichero_que_no_es_imagen_no_revienta` | Un `.png` falso no rompe el programa: queda como fallo con un mensaje que habla de «imagen». |

### `test_tipos_web.py`

La *fixture* `web` crea una mini web falsa con `plantilla.md`, prompts 05 y 18
y un `sw.js` con saltos de línea de Windows (`\r\n`).

| Prueba | Qué comprueba la aserción |
| --- | --- |
| `test_crear_usa_el_numero_siguiente_y_rellena_la_plantilla` | Crea `19-tronker-en-discord.md` (18 + 1) con el título y la fecha puestos. |
| `test_crear_sin_texto_es_error_de_uso` | Sin `--texto`: `ErrorUso` que lo pide. |
| `test_crear_fuera_del_proyecto_es_error_de_uso` | Si no encuentra el modelo (estás en otra carpeta), `ErrorUso`. |
| `test_incrementar_cambia_solo_el_numero_y_respeta_crlf` | `6` pasa a `7` y el resto del fichero, incluidos los `\r\n`, queda **byte a byte** igual. |
| `test_incrementar_sin_coincidencia_se_omite` | Si el patrón no aparece, no hace nada y lo dice. |
| `test_informe_lista_lo_pesado_sin_tocar_nada` | Solo sale el fichero de 300 KB (el filtro es > 200 KB), con su tamaño legible. |
| `test_comprimir_sin_git_y_sin_meterse_a_si_misma` | El zip lleva `sw.js` y `.gitignore`, pero nada de `.git/` ni la propia carpeta de copias. |

### `test_cli.py`

`CliRunner` lanza la CLI como si la escribieras en la terminal y guarda la
salida y el código.

| Prueba | Qué comprueba la aserción |
| --- | --- |
| `test_version` | Sale con 0 y escribe la versión. |
| `test_listar_json` | `--json` da JSON válido con nombre (con tilde), tipo y tamaño. |
| `test_listar_carpeta_que_no_existe` | Código 2 (error de uso). |
| `test_validar_invalido_sale_con_3` | Código 3 y el mensaje nombra el campo `descripcion`. |
| `test_ejecutar_simular_y_de_verdad` | `--simular` no borra; sin `--si` y sin terminal se niega (código 2); con `--si` borra. |
| `test_consola_cp1252_no_revienta_con_simbolos` | Lanza la CLI de verdad con la consola en cp1252 (como Windows) y sale con 0. |

## Preguntas típicas de defensa

- **¿Cómo añado una acción?** Editando `acciones.json` y `tareas validar`. No se toca el código.
- **¿Y un tipo nuevo?** Clase en `acciones.py`, añadirla a `TIPOS`, sus campos en `config.py` y una prueba.
- **¿Qué pasa si no hay red?** Nada: ninguna acción actual la usa.
- **¿Dónde están las claves?** No hay. Cuando haya IA, en `.env`, que está en `.gitignore` desde el primer commit.
- **¿Por qué uv?** Instala Python, las dependencias y la herramienta como comando con una orden.
