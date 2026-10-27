"""Interfaz Typer: órdenes, opciones y salida. Habla con la persona; el trabajo lo hace el Motor."""

import json
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Iterator

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from tareas import __version__
from tareas.acciones import Operacion, tamano_legible
from tareas.config import Configuracion, buscar_config
from tareas.errores import ConfigError, ErrorUso, TareasError
from tareas.motor import Motor, Plan

app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="rich",
)
salida = Console()
errores = Console(stderr=True)

RESPUESTAS_SI = {"s", "si", "sí", "y", "yes"}


@contextmanager
def _sin_traceback() -> Iterator[None]:
    """Convierte nuestros errores previsibles en un mensaje y su código de salida."""
    try:
        yield
    except ConfigError as e:
        errores.print(f"[red]Error de configuración:[/red] {escape(str(e))}")
        for detalle in e.errores:
            errores.print(f"  [red]✗[/red] {escape(detalle)}")
        raise typer.Exit(e.codigo_salida) from None
    except TareasError as e:
        errores.print(f"[red]Error:[/red] {escape(str(e))}")
        raise typer.Exit(e.codigo_salida) from None


def _cargar(ctx: typer.Context) -> Configuracion:
    return Configuracion.desde_fichero(buscar_config(ctx.obj["config"]))


@app.callback()
def principal(
    ctx: typer.Context,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Fichero de acciones. Por defecto: ./acciones.json y, si no está, el de tu usuario.",
            envvar="TAREAS_CONFIG",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Ejecuta sobre tus ficheros las acciones que defines en acciones.json.

    Códigos de salida: 0 bien · 1 fallo al ejecutar · 2 error de uso · 3 configuración inválida.
    """
    ctx.obj = {"config": config.expanduser() if config else None}


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    typer.echo(f"tareas {__version__}")


@app.command()
def listar(
    carpeta: Annotated[
        Path, typer.Argument(help="Carpeta a listar (por defecto, la actual).", show_default=False)
    ] = Path("."),
    como_json: Annotated[bool, typer.Option("--json", help="Salida JSON para otros programas.")] = False,
) -> None:
    """Tabla con nombre, tipo, tamaño y fecha de cada fichero de CARPETA."""
    with _sin_traceback():
        carpeta = carpeta.expanduser()
        if not carpeta.is_dir():
            raise ErrorUso(f"La carpeta {carpeta} no existe o no es una carpeta.")
        try:
            entradas = sorted(carpeta.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            filas = [_describir(p) for p in entradas]
        except PermissionError:
            raise ErrorUso(f"No tengo permiso para leer {carpeta}.") from None

    if como_json:
        typer.echo(json.dumps(filas, ensure_ascii=False, indent=2))
        return

    tabla = Table(title=escape(str(carpeta.resolve())), title_justify="left")
    tabla.add_column("Nombre")
    tabla.add_column("Tipo")
    tabla.add_column("Tamaño", justify="right")
    tabla.add_column("Modificado")
    for fila in filas:
        es_carpeta = fila["tipo"] == "carpeta"
        tabla.add_row(
            f"[bold blue]{escape(fila['nombre'])}/[/]" if es_carpeta else escape(fila["nombre"]),
            fila["tipo"],
            "" if es_carpeta else tamano_legible(fila["tamano_bytes"]),
            fila["modificado"].replace("T", " ")[:16],
        )
    salida.print(tabla)
    salida.print(f"{len(filas)} elementos")


def _describir(ruta: Path) -> dict:
    info = ruta.stat()
    es_carpeta = ruta.is_dir()
    return {
        "nombre": ruta.name,
        "tipo": "carpeta" if es_carpeta else (ruta.suffix.lower().lstrip(".") or "fichero"),
        "tamano_bytes": None if es_carpeta else info.st_size,
        "modificado": datetime.fromtimestamp(info.st_mtime).isoformat(timespec="seconds"),
    }


@app.command("acciones")
def listar_acciones(
    ctx: typer.Context,
    como_json: Annotated[bool, typer.Option("--json", help="Salida JSON para otros programas.")] = False,
) -> None:
    """Lista las acciones definidas en acciones.json."""
    with _sin_traceback():
        conf = _cargar(ctx)
    if como_json:
        datos = [{"nombre": a.nombre, "tipo": a.tipo, "descripcion": a.descripcion} for a in conf.acciones]
        typer.echo(json.dumps(datos, ensure_ascii=False, indent=2))
        return
    tabla = Table(title=escape(str(conf.ruta)), title_justify="left")
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Tipo")
    tabla.add_column("Descripción")
    for a in conf.acciones:
        tabla.add_row(escape(a.nombre), a.tipo, escape(a.descripcion))
    salida.print(tabla)


@app.command()
def validar(ctx: typer.Context) -> None:
    """Comprueba acciones.json y dice qué campo falla (código 3 si es inválido)."""
    with _sin_traceback():
        conf = _cargar(ctx)
    salida.print(f"[green]✓[/green] {escape(str(conf.ruta))} es válido: {len(conf.acciones)} acciones.")


@app.command()
def ejecutar(
    ctx: typer.Context,
    nombre: Annotated[str, typer.Argument(help="Acción a ejecutar (mira «tareas acciones»).")],
    carpeta: Annotated[
        Path | None,
        typer.Argument(help="Carpeta sobre la que actuar. Si no se da: «origen» de la acción o la actual."),
    ] = None,
    simular: Annotated[bool, typer.Option("--simular", help="Enseña qué haría, sin tocar nada.")] = False,
    si: Annotated[bool, typer.Option("--si", help="No pregunta antes de actuar (para scripts).")] = False,
    texto: Annotated[
        str | None, typer.Option("--texto", "-t", help="Título para las acciones que crean ficheros.")
    ] = None,
) -> None:
    """Ejecuta la acción NOMBRE sobre CARPETA."""
    with _sin_traceback():
        accion = _cargar(ctx).buscar(nombre)
        plan = Motor().planificar(accion, carpeta, texto)

    _mostrar_plan(plan, simulacion=simular and not accion.solo_lectura)
    if simular or accion.solo_lectura or not plan.pendientes:
        return

    if accion.confirmar and not si:
        if not sys.stdin.isatty():
            errores.print("[red]Error:[/red] esta acción pide confirmación; en un script usa --si.")
            raise typer.Exit(2)
        respuesta = salida.input(f"¿Seguro que quieres {accion.tipo} {len(plan.pendientes)} ficheros? [s/N] ")
        if respuesta.strip().lower() not in RESPUESTAS_SI:
            salida.print("Cancelado: no se ha tocado nada.")
            return

    resultado = Motor.ejecutar(plan)
    for op, motivo in resultado.fallos:
        errores.print(f"[red]✗[/red] {escape(op.origen.name)}: {escape(motivo)}")
    color = "green" if resultado.ok else "yellow"
    salida.print(
        f"[{color}]Hecho:[/{color}] {len(resultado.hechas)} correctos, "
        f"{len(resultado.fallos)} con error, {len(plan.omitidas)} omitidos."
    )
    if not resultado.ok:
        raise typer.Exit(1)


def _mostrar_plan(plan: Plan, simulacion: bool) -> None:
    accion = plan.accion
    cabecera = "[bold yellow]SIMULACIÓN[/] · " if simulacion else ""
    salida.print(f"{cabecera}[bold]{escape(accion.nombre)}[/] ({accion.tipo}) en {escape(str(plan.carpeta))}")
    if not plan.operaciones:
        if accion.solo_lectura:
            salida.print("[green]✓[/green] Ningún fichero cumple el filtro.")
        else:
            salida.print("Ningún fichero coincide con el filtro: nada que hacer.")
        return
    if accion.solo_lectura:
        for op in plan.operaciones:
            salida.print(f"  [yellow]![/] {escape(_relativa(op.origen, plan.carpeta))}  {escape(op.detalle or '')}")
        salida.print(f"{len(plan.operaciones)} ficheros.")
        return
    for op in plan.operaciones:
        texto = _describir_operacion(op, plan.carpeta)
        if op.detalle:
            texto += f" [dim]({escape(op.detalle)})[/]"
        if op.omitida:
            salida.print(f"  [yellow]·[/] {texto} [yellow](se omite: {escape(op.omitida)})[/]")
        else:
            salida.print(f"  [cyan]→[/] {texto}")
    salida.print(f"{len(plan.pendientes)} operaciones, {len(plan.omitidas)} omitidas.")
    if simulacion:
        salida.print("[yellow]Simulación: no se ha tocado nada.[/]")


def _describir_operacion(op: Operacion, carpeta: Path) -> str:
    origen = escape(_relativa(op.origen, carpeta))
    if op.destino is None:
        return origen
    if op.origen.is_dir():
        return f"toda la carpeta → {escape(str(op.destino))}"
    if op.destino.parent == op.origen.parent:
        return f"{origen} → {escape(op.destino.name)}"
    return f"{origen} → {escape(str(op.destino))}"


def _relativa(ruta: Path, carpeta: Path) -> str:
    try:
        return str(ruta.relative_to(carpeta))
    except ValueError:
        return str(ruta)
