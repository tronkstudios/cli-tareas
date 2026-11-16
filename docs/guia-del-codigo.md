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
| `ia.py` | Hablar con el modelo de IA. `ProveedorIA` es abstracta; `ProveedorOpenAI` hace la petición HTTP con `urllib`. | ¿Por qué abstracta? El motor y las pruebas no saben qué modelo hay detrás: en las pruebas se usa `ProveedorFalso` y nunca hay red. |
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

### Ideas que salen en la capa de IA

- **Importación perezosa**: `ia.py` solo se importa dentro de `Motor.ejecutar()`
  y de `comprobar-ia`. Sin red ni configuración, `tareas acciones`, `--simular`
  y las acciones normales ni se enteran.
- **Inyección de dependencias**: `Motor.ejecutar(plan, proveedor)` recibe el
  proveedor. Si no se da, lo crea `ProveedorIA.desde_entorno()` (otra fábrica
  estática). Las pruebas le pasan un `ProveedorFalso`.
- **Planificar no llama al modelo**: `AccionIA.preparar()` solo lee los
  ficheros o ejecuta `git log`/`git diff` y cuenta caracteres. La llamada,
  que es lenta y cuesta, ocurre en `aplicar()`.
- **`subprocess.run([...])` con lista**: nunca `shell=True`. Un nombre de
  carpeta con espacios o comillas no puede inyectar órdenes.
- **Visibilidad**: la clave se guarda en `self.__clave` (doble guion bajo:
  Python le cambia el nombre) y `__repr__` no la enseña. Ningún mensaje de
  error la incluye; hay una prueba que lo comprueba.
- **Errores con nombre**: un 401 es `IASinConfigurar`; sin red, un 503 o un
  timeout son `IASinConexion`. Un error de IA para toda la acción (no tiene
  sentido seguir); un fichero que no se puede escribir solo ese fichero.
- **`<think>…</think>`**: los modelos Qwen «piensan en voz alta»; se borra
  antes de guardar la respuesta.

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

### `test_ia.py`

Un servidor HTTP de mentira escucha en `127.0.0.1` y responde según el modelo
pedido: bien, 503, 401 o algo que no es JSON. `ProveedorFalso` contesta sin
red y apunta cada llamada.

| Prueba | Qué comprueba la aserción |
| --- | --- |
| `test_sin_variables_es_ia_sin_configurar` | Sin variables ni `.env`: `IASinConfigurar` nombrando la que falta. |
| `test_lee_el_env_de_la_carpeta_actual` | Lee `.env` y `repr()` del proveedor no contiene la clave. |
| `test_respuesta_correcta_sin_el_pensamiento` | Quita `<think>…</think>` y espacios; manda la clave como `Bearer` y los mensajes `system` + `user`. |
| `test_errores_del_servidor_con_mensaje_humano_y_sin_la_clave` | 503, 401 y JSON roto dan la excepción y el mensaje correctos, y ninguno contiene la clave. |
| `test_sin_conexion` | Un puerto donde no escucha nadie: `IASinConexion` «No hay conexión». |
| `test_simular_no_llama_al_modelo` | El plan existe, pero no se ha creado ninguna respuesta. |
| `test_ficheros_crea_respuestas_y_no_se_resume_a_si_misma` | Crea `a.resumen.md`, no sobrescribe `b.resumen.md`, omite el PNG, no resume los `.resumen.md` y llama al modelo **una sola vez**. |
| `test_recorta_textos_largos` | Avisa del recorte en el plan y al modelo le llegan 100 caracteres. |
| `test_sin_salida_la_respuesta_vuelve_para_la_pantalla` | Sin `salida` no se crea ningún fichero y la respuesta vuelve en `Resultado.respuestas`. |
| `test_git_log_manda_los_commits` | En un repo temporal, el mensaje del commit llega al modelo. |
| `test_git_diff_sin_cambios_se_omite_y_con_cambios_se_manda` | Sin cambios se omite; con un cambio, el diff (`+dos`) llega al modelo. |
| `test_git_fuera_de_un_repo_es_error_de_uso` | Fuera de un repo, `ErrorUso` (código 2). |
| `test_validacion_de_la_accion_ia` | Detecta `instrucciones` que falta, `entrada` inválida, `commits` 0 y `..` en la salida. |
| `test_comprobar_ia_sin_configurar` | Código 1, mensaje «Falta configurar» y ningún traceback. |
| `test_sin_red_la_accion_ia_falla_en_una_linea_y_las_demas_siguen` | La de IA sale con 1 sin traceback ni clave; justo después, una acción normal funciona. |
| `test_acciones_marca_las_de_ia` | `tareas acciones --json` marca `"ia": true` solo en la de IA. |

## Preguntas típicas de defensa

- **¿Cómo añado una acción?** Editando `acciones.json` y `tareas validar`. No se toca el código.
- **¿Y un tipo nuevo?** Clase en `acciones.py`, añadirla a `TIPOS`, sus campos en `config.py` y una prueba.
- **¿Qué pasa si no hay red?** Las acciones de IA lo dicen en una línea y salen con código 1; las otras 10 funcionan igual porque `ia.py` ni se carga. `--simular` nunca llama al modelo.
- **¿Dónde está la clave?** En `TAREAS_IA_CLAVE`, como variable de entorno o en un `.env` que está en `.gitignore` desde el primer commit. En el repo solo hay `.env.example` con valores falsos.
- **¿Por qué no el SDK de OpenAI?** Una sola petición HTTP no lo justifica, y con `urllib` vale para cualquier servidor compatible (ADR 0002).
- **¿Cómo cambio lo que hace una acción de IA?** Cambiando sus `instrucciones` en `acciones.json`.
- **¿Por qué uv?** Instala Python, las dependencias y la herramienta como comando con una orden.
