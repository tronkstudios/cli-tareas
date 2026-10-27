"""Leer y VALIDAR acciones.json. Desconfía de todo lo que venga del fichero."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tareas.acciones import TIPOS, Accion
from tareas.errores import AccionNoEncontrada, AccionNoValida, ConfigError

VERSION_ESQUEMA = 1
RUTA_POR_DEFECTO = Path("acciones.json")

_NOMBRE_VALIDO = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_CAMPOS_COMUNES = {"nombre", "descripcion", "tipo", "origen", "filtro", "confirmar"}
_CAMPOS_POR_TIPO = {
    "mover": {"destino"},
    "copiar": {"destino"},
    "renombrar": {"plantilla"},
    "borrar": set(),
    "webp": set(),
}
_CAMPOS_OPCIONALES = {"webp": {"destino", "ancho_max", "calidad"}}
_CAMPOS_FILTRO = {"extensiones", "patron", "mas_antiguo_que_dias", "recursivo"}


@dataclass(frozen=True)
class Configuracion:
    """El contenido de acciones.json ya validado y convertido en objetos Accion."""

    ruta: Path
    acciones: tuple[Accion, ...]

    @staticmethod
    def desde_fichero(ruta: Path) -> "Configuracion":
        """Lee, valida y construye la configuración. Lanza ConfigError si algo falla."""
        ruta = Path(ruta).expanduser()
        datos = _leer_json(ruta)
        errores = validar(datos)
        if errores:
            raise ConfigError(f"{ruta} no es válido", errores)
        acciones = tuple(Accion.desde_dict(a) for a in datos["acciones"])
        return Configuracion(ruta=ruta, acciones=acciones)

    def buscar(self, nombre: str) -> Accion:
        for accion in self.acciones:
            if accion.nombre == nombre:
                return accion
        disponibles = ", ".join(a.nombre for a in self.acciones) or "ninguna"
        raise AccionNoEncontrada(
            f"No existe la acción «{nombre}». Disponibles: {disponibles}"
        )


def _leer_json(ruta: Path) -> Any:
    if not ruta.exists():
        raise ConfigError(
            f"No encuentro {ruta}. Créalo o indica otro con --config RUTA."
        )
    if not ruta.is_file():
        raise ConfigError(f"{ruta} no es un fichero.")
    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ConfigError(f"{ruta} no está guardado en UTF-8.") from None
    except OSError as e:
        raise ConfigError(f"No puedo leer {ruta}: {e.strerror}") from None
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"{ruta} no es JSON válido (línea {e.lineno}, columna {e.colno}): {e.msg}"
        ) from None


def validar(datos: Any) -> list[str]:
    """Devuelve la lista de errores del esquema; vacía si todo está bien.

    Cada error empieza por la ruta del campo, p. ej. «acciones[1].filtro.extensiones».
    """
    if not isinstance(datos, dict):
        return ["raíz: debe ser un objeto JSON { ... }"]

    errores: list[str] = []
    version = datos.get("version")
    if version is None:
        errores.append("version: falta (usa 1)")
    elif version != VERSION_ESQUEMA:
        errores.append(f"version: {version!r} no soportada (usa {VERSION_ESQUEMA})")

    acciones = datos.get("acciones")
    if acciones is None:
        errores.append("acciones: falta la lista de acciones")
        return errores
    if not isinstance(acciones, list):
        errores.append("acciones: debe ser una lista [ ... ]")
        return errores
    if not acciones:
        errores.append("acciones: la lista está vacía")

    vistos: set[str] = set()
    for i, accion in enumerate(acciones):
        errores.extend(_validar_accion(accion, f"acciones[{i}]", vistos))
    return errores


def _validar_accion(accion: Any, donde: str, vistos: set[str]) -> list[str]:
    if not isinstance(accion, dict):
        return [f"{donde}: debe ser un objeto {{ ... }}"]
    errores: list[str] = []

    nombre = accion.get("nombre")
    if not isinstance(nombre, str) or not nombre:
        errores.append(f"{donde}.nombre: falta o no es un texto")
    else:
        donde = f"{donde} ({nombre})"
        if not _NOMBRE_VALIDO.match(nombre):
            errores.append(f"{donde}.nombre: solo minúsculas, números y guiones")
        if nombre in vistos:
            errores.append(f"{donde}.nombre: está repetido")
        vistos.add(nombre)

    if not isinstance(accion.get("descripcion"), str) or not accion["descripcion"].strip():
        errores.append(f"{donde}.descripcion: falta o está vacía")

    tipo = accion.get("tipo")
    if tipo not in TIPOS:
        errores.append(
            f"{donde}.tipo: {tipo!r} no es válido (usa: {', '.join(sorted(TIPOS))})"
        )
        return errores

    permitidos = _CAMPOS_COMUNES | _CAMPOS_POR_TIPO[tipo] | _CAMPOS_OPCIONALES.get(tipo, set())
    for campo in sorted(set(accion) - permitidos):
        errores.append(f"{donde}.{campo}: campo desconocido para el tipo {tipo}")

    for campo in sorted(_CAMPOS_POR_TIPO[tipo]):
        valor = accion.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            errores.append(f"{donde}.{campo}: obligatorio para el tipo {tipo}")

    if "origen" in accion and (not isinstance(accion["origen"], str) or not accion["origen"]):
        errores.append(f"{donde}.origen: debe ser una ruta (texto)")

    if "destino" in accion and (not isinstance(accion["destino"], str) or not accion["destino"].strip()):
        if tipo == "webp":
            errores.append(f"{donde}.destino: debe ser una ruta (texto)")

    for campo, minimo, maximo in (("ancho_max", 1, 20000), ("calidad", 1, 100)):
        if campo in accion:
            valor = accion[campo]
            if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
                errores.append(f"{donde}.{campo}: debe ser un entero entre {minimo} y {maximo}")

    if "confirmar" in accion and not isinstance(accion["confirmar"], bool):
        errores.append(f"{donde}.confirmar: debe ser true o false")

    if isinstance(accion.get("plantilla"), str):
        errores.extend(_validar_plantilla(accion["plantilla"], f"{donde}.plantilla"))

    if "filtro" in accion:
        errores.extend(_validar_filtro(accion["filtro"], f"{donde}.filtro"))
    return errores


def _validar_plantilla(plantilla: str, donde: str) -> list[str]:
    try:
        resultado = plantilla.format(
            fecha=datetime(2026, 1, 1), n=1, ext=".txt", nombre="Ejemplo", slug="ejemplo"
        )
    except (KeyError, IndexError) as e:
        return [f"{donde}: variable desconocida {e} (usa fecha, n, ext, nombre, slug)"]
    except ValueError as e:
        return [f"{donde}: formato incorrecto ({e})"]
    if not resultado.strip() or any(sep in resultado for sep in ("/", "\\")):
        return [f"{donde}: debe dar un nombre de fichero, sin / ni \\"]
    return []


def _validar_filtro(filtro: Any, donde: str) -> list[str]:
    if not isinstance(filtro, dict):
        return [f"{donde}: debe ser un objeto {{ ... }}"]
    errores = [
        f"{donde}.{campo}: campo desconocido (usa: {', '.join(sorted(_CAMPOS_FILTRO))})"
        for campo in sorted(set(filtro) - _CAMPOS_FILTRO)
    ]

    if "extensiones" in filtro:
        ext = filtro["extensiones"]
        if not isinstance(ext, list) or not ext or not all(isinstance(e, str) for e in ext):
            errores.append(f"{donde}.extensiones: debe ser una lista de textos, p. ej. [\".pdf\"]")
        else:
            for e in ext:
                if not e.startswith(".") or len(e) < 2:
                    errores.append(f"{donde}.extensiones: «{e}» debe empezar por punto, p. ej. \".pdf\"")

    if "patron" in filtro:
        patron = filtro["patron"]
        if not isinstance(patron, str):
            errores.append(f"{donde}.patron: debe ser un texto (expresión regular)")
        else:
            try:
                re.compile(patron)
            except re.error as e:
                errores.append(f"{donde}.patron: expresión regular incorrecta ({e})")

    if "mas_antiguo_que_dias" in filtro:
        dias = filtro["mas_antiguo_que_dias"]
        if isinstance(dias, bool) or not isinstance(dias, (int, float)) or dias < 0:
            errores.append(f"{donde}.mas_antiguo_que_dias: debe ser un número >= 0")

    if "recursivo" in filtro and not isinstance(filtro["recursivo"], bool):
        errores.append(f"{donde}.recursivo: debe ser true o false")
    return errores
