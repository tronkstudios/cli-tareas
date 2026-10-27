# ADR 0001 · Las acciones viven en acciones.json, no en el código

- **Estado:** aceptada
- **Fecha:** 27 de octubre de 2026

## Contexto

`tareas` tiene que hacer trabajos que cambian a menudo: hoy las miniaturas de
las tarjetas se hacen a 480 px; mañana puede que a 640. Hoy los vídeos van a
`video/`; mañana puede haber otra carpeta. Si cada acción fuera una función en
Python, cualquier cambio exigiría tocar el código, reinstalar y arriesgarse a
romper otra cosa.

## Decisión

El código solo conoce **tipos** de acción (`mover`, `copiar`, `renombrar`,
`borrar`, `webp`), cada uno en una clase de `acciones.py`. Las **acciones
concretas** (qué carpeta, qué extensiones, qué ancho, qué plantilla) se
describen en `acciones.json`, que `config.py` valida antes de usar.

- Añadir o cambiar una acción = editar el JSON. `tareas validar` dice qué
  campo falla y sale con código 3.
- Solo hace falta tocar el código para un **tipo** nuevo.
- Se puede tener otro fichero para otro proyecto: `tareas --config otro.json`.

## Consecuencias

- 👍 Las acciones se leen como documentación y se pueden revisar en un PR.
- 👍 El motor se prueba una vez por tipo, no una vez por acción.
- 👎 Hay que mantener un validador: un JSON mal escrito no lo detecta Python.
- 👎 Lo que no se puede expresar con los campos de un tipo necesita un tipo nuevo.

## Alternativas descartadas

- **Acciones escritas en Python (una función por acción):** más flexible, pero
  cada cambio es código, y quien solo quiere cambiar un ancho tiene que leerlo.
- **YAML o TOML:** más cómodos de escribir, pero JSON viene con Python sin
  dependencias y es lo que pide el proyecto.
