# ADR 0002 · Un proveedor de IA abstracto, sin SDK, y las instrucciones en el JSON

- **Estado:** aceptada
- **Fecha:** 16 de noviembre de 2026

## Contexto

`tareas` tenía que usar los modelos de IA del centro (Qwen, detrás de LiteLLM,
con una API compatible con OpenAI y un certificado propio). Al probarlos, los
modelos devolvían a menudo `503 Service Unavailable` y el certificado no era de
confianza para `curl`, Node ni Python. Además, las pruebas tienen que pasar en
GitHub Actions, donde no hay ni red al centro ni clave.

## Decisión

1. **`ProveedorIA` abstracto** con un único método, `completar(instrucciones, texto)`.
   El motor y las acciones solo conocen esa clase. `ProveedorOpenAI` es la
   implementación real y `ProveedorIA.desde_entorno()` la fábrica.
2. **Sin SDK, con `urllib`.** Una petición `POST /chat/completions` no
   justifica una dependencia más, y así funciona con LiteLLM, vLLM, Ollama u
   OpenAI cambiando solo `TAREAS_IA_URL` y `TAREAS_IA_MODELO`.
3. **Configuración solo por entorno** (`TAREAS_IA_URL`, `TAREAS_IA_MODELO`,
   `TAREAS_IA_CLAVE`, opcionales `TAREAS_IA_CA` y `TAREAS_IA_ESPERA`), con
   `.env` ignorado por git y `.env.example` documentado. La clave es un
   atributo privado y no aparece en mensajes ni en `repr`.
4. **Certificado propio con `TAREAS_IA_CA`**: se añade a los de confianza.
   La verificación TLS nunca se desactiva.
5. **Las instrucciones para el modelo van en `acciones.json`**, igual que el
   resto de acciones (ADR 0001): cambiar lo que se pide no exige tocar código.
6. **`ia.py` se importa solo al usarlo** y planificar no llama al modelo: sin
   red, `--simular` y las demás acciones funcionan igual.
7. **Errores con nombre**: `IASinConfigurar` (faltan variables, clave
   rechazada, 404) e `IASinConexion` (sin red, 503, tiempo agotado, respuesta
   vacía o rara), con mensajes de una línea. Las respuestas de modelos que
   «piensan» se limpian de `<think>…</think>`.

## Consecuencias

- 👍 Las pruebas usan un `ProveedorFalso` y un servidor HTTP local: nunca la red.
- 👍 Cambiar de modelo o de servidor es cambiar dos variables.
- 👎 No hay streaming: con modelos lentos hay que esperar la respuesta entera
  (por eso `TAREAS_IA_ESPERA`).
- 👎 Si algún día hace falta algo que solo da un SDK (imágenes, herramientas),
  habrá que añadir otra subclase de `ProveedorIA`.

## Alternativas descartadas

- **SDK de `openai`:** dependencia grande para una sola llamada, y ata el código a un proveedor.
- **Llamar al modelo desde `cli.py`:** mezclaría interfaz y trabajo, y no se podría probar sin red.
- **Instrucciones escritas en el código:** contradice el ADR 0001.
- **`verify=False` para el certificado del centro:** la clave viajaría sin protección.
