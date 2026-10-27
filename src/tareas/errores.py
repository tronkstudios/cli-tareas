"""Excepciones propias de tareas.

Cada una lleva el código de salida que debe devolver la CLI:
0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
"""


class TareasError(Exception):
    """Error previsible: la CLI lo muestra en una línea, sin traceback."""

    codigo_salida = 1


class ErrorUso(TareasError):
    """La orden está bien escrita pero sus datos no valen (p. ej., carpeta inexistente)."""

    codigo_salida = 2


class ConfigError(TareasError):
    """acciones.json no existe, no es JSON válido o no cumple el esquema."""

    codigo_salida = 3

    def __init__(self, mensaje: str, errores: list[str] | None = None):
        super().__init__(mensaje)
        self.errores = errores or []


class AccionNoValida(ConfigError):
    """Una acción concreta tiene un campo que falta o es incorrecto."""


class AccionNoEncontrada(ErrorUso):
    """Se pidió ejecutar una acción que no está en acciones.json."""
