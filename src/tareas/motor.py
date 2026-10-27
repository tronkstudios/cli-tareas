"""Motor: ejecuta una Accion sobre una carpeta. No sabe nada de Typer ni de colores."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tareas.acciones import Accion, Operacion
from tareas.errores import ErrorUso


@dataclass
class Plan:
    """Lo que haría una acción: se enseña con --simular y se ejecuta sin él."""

    accion: Accion
    carpeta: Path
    operaciones: list[Operacion]

    @property
    def pendientes(self) -> list[Operacion]:
        return [op for op in self.operaciones if op.omitida is None]

    @property
    def omitidas(self) -> list[Operacion]:
        return [op for op in self.operaciones if op.omitida is not None]


@dataclass
class Resultado:
    hechas: list[Operacion] = field(default_factory=list)
    fallos: list[tuple[Operacion, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fallos


class Motor:
    """Separa el QUÉ (planificar) del HACER (ejecutar)."""

    def __init__(self, ahora: datetime | None = None):
        self._ahora = ahora or datetime.now()

    def planificar(self, accion: Accion, carpeta_orden: Path | None = None) -> Plan:
        carpeta = accion.carpeta_de_trabajo(carpeta_orden)
        if not carpeta.exists():
            raise ErrorUso(f"La carpeta {carpeta} no existe.")
        if not carpeta.is_dir():
            raise ErrorUso(f"{carpeta} no es una carpeta.")
        try:
            ficheros = accion.seleccionar(carpeta, self._ahora)
        except PermissionError:
            raise ErrorUso(f"No tengo permiso para leer {carpeta}.") from None
        return Plan(accion, carpeta, accion.planificar(ficheros, carpeta))

    @staticmethod
    def ejecutar(plan: Plan) -> Resultado:
        """Aplica cada operación pendiente. Un fallo no detiene las demás."""
        resultado = Resultado()
        for op in plan.pendientes:
            try:
                plan.accion.aplicar(op)
            except OSError as e:
                resultado.fallos.append((op, e.strerror or str(e)))
            else:
                resultado.hechas.append(op)
        return resultado
