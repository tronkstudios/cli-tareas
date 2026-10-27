"""Clases Accion: una por cada «tipo» de acciones.json.

Una acción sabe dos cosas: PLANIFICAR qué haría con cada fichero (sin tocar nada)
y APLICAR una operación concreta. Quién decide cuándo aplicar es el Motor.
"""

import re
import shutil
import unicodedata
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from tareas.errores import AccionNoValida, ErrorUso


@dataclass(frozen=True)
class Filtro:
    """Qué ficheros le afectan a una acción. Sin campos, le afectan todos."""

    extensiones: tuple[str, ...] = ()
    patron: re.Pattern[str] | None = None
    mas_antiguo_que_dias: float | None = None
    mas_grande_que_kb: float | None = None
    recursivo: bool = False

    @staticmethod
    def desde_dict(datos: dict[str, Any] | None) -> "Filtro":
        datos = datos or {}
        patron = datos.get("patron")
        return Filtro(
            extensiones=tuple(e.lower() for e in datos.get("extensiones", [])),
            patron=re.compile(patron) if patron else None,
            mas_antiguo_que_dias=datos.get("mas_antiguo_que_dias"),
            mas_grande_que_kb=datos.get("mas_grande_que_kb"),
            recursivo=datos.get("recursivo", False),
        )

    def coincide(self, fichero: Path, ahora: datetime) -> bool:
        if self.extensiones and fichero.suffix.lower() not in self.extensiones:
            return False
        if self.patron and not self.patron.search(fichero.name):
            return False
        if self.mas_antiguo_que_dias is not None:
            modificado = datetime.fromtimestamp(fichero.stat().st_mtime)
            if ahora - modificado < timedelta(days=self.mas_antiguo_que_dias):
                return False
        if self.mas_grande_que_kb is not None:
            if fichero.stat().st_size <= self.mas_grande_que_kb * 1024:
                return False
        return True


@dataclass(frozen=True)
class Operacion:
    """Un paso concreto sobre un fichero. Si «omitida» tiene texto, no se hará."""

    origen: Path
    destino: Path | None = None
    omitida: str | None = None
    detalle: str | None = None  # dato extra para enseñar (tamaño, número nuevo…)
    contenido: str | None = None  # texto a escribir, para los tipos que crean ficheros


@dataclass(frozen=True)
class Accion(ABC):
    """Base de todas las acciones. Las subclases definen planificar() y aplicar()."""

    nombre: str
    descripcion: str
    origen: str | None = None
    filtro: Filtro = field(default_factory=Filtro)
    confirmar: bool = False

    tipo: ClassVar[str]
    solo_lectura: ClassVar[bool] = False  # True: solo informa, nunca toca el disco

    @staticmethod
    def desde_dict(datos: dict[str, Any]) -> "Accion":
        """Fábrica: crea la subclase adecuada según datos["tipo"].

        Espera datos ya validados por config.validar().
        """
        clase = TIPOS.get(datos.get("tipo"))
        if clase is None:
            raise AccionNoValida(f"Tipo de acción desconocido: {datos.get('tipo')!r}")
        return clase(**clase._argumentos(datos))

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        """Campos del JSON → argumentos del constructor. Las subclases añaden los suyos."""
        return {
            "nombre": datos["nombre"],
            "descripcion": datos["descripcion"],
            "origen": datos.get("origen"),
            "filtro": Filtro.desde_dict(datos.get("filtro")),
            "confirmar": datos.get("confirmar", False),
        }

    def carpeta_de_trabajo(self, carpeta_orden: Path | None) -> Path:
        """La CARPETA de la orden manda; si no hay, «origen»; si tampoco, la actual."""
        if carpeta_orden is not None:
            return carpeta_orden.expanduser()
        if self.origen:
            return Path(self.origen).expanduser()
        return Path.cwd()

    def seleccionar(self, carpeta: Path, ahora: datetime) -> list[Path]:
        """Ficheros de la carpeta que pasan el filtro, en orden estable.

        En modo recursivo no entra en carpetas ocultas (.git, .venv…). Los ficheros
        ocultos (.DS_Store…) solo se eligen si el filtro tiene un «patron» que los nombre.
        """
        candidatos = carpeta.rglob("*") if self.filtro.recursivo else carpeta.iterdir()
        elegidos = [
            f
            for f in candidatos
            if f.is_file()
            and not f.is_symlink()
            and not any(p.startswith(".") for p in f.relative_to(carpeta).parts[:-1])
            and (self.filtro.patron is not None or not f.name.startswith("."))
            and self.filtro.coincide(f, ahora)
        ]
        return sorted(elegidos, key=lambda f: (f.stat().st_mtime, f.name))

    def preparar(self, carpeta: Path, ahora: datetime, texto: str | None) -> list[Operacion]:
        """Punto de entrada del Motor. Por defecto: elegir ficheros y planificar sobre ellos.

        Los tipos que no trabajan fichero a fichero (crear, incrementar, comprimir) lo redefinen.
        """
        return self.planificar(self.seleccionar(carpeta, ahora), carpeta)

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        """Decide qué se haría con cada fichero. NO toca el disco."""
        raise NotImplementedError

    @abstractmethod
    def aplicar(self, operacion: Operacion) -> None:
        """Hace UNA operación de verdad. Puede lanzar OSError."""


@dataclass(frozen=True)
class _AccionConDestino(Accion):
    """Base para mover y copiar: llevan los ficheros a otra carpeta."""

    destino: str = ""

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {**super()._argumentos(datos), "destino": datos["destino"]}

    def carpeta_destino(self, carpeta: Path) -> Path:
        """Un destino relativo se entiende dentro de la carpeta de trabajo."""
        destino = Path(self.destino).expanduser()
        return destino if destino.is_absolute() else carpeta / destino

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        destino_dir = self.carpeta_destino(carpeta)
        ops = []
        for f in ficheros:
            destino = destino_dir / f.name
            if f.resolve().is_relative_to(destino_dir.resolve()):
                continue  # ya está dentro del destino
            if destino.exists():
                ops.append(Operacion(f, destino, omitida="ya existe en el destino"))
            else:
                ops.append(Operacion(f, destino))
        return ops

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.destino is not None and operacion.omitida is None
        if operacion.destino.exists():
            raise FileExistsError(f"ya existe {operacion.destino}")
        operacion.destino.parent.mkdir(parents=True, exist_ok=True)
        self._transferir(operacion.origen, operacion.destino)

    @staticmethod
    @abstractmethod
    def _transferir(origen: Path, destino: Path) -> None: ...


@dataclass(frozen=True)
class AccionMover(_AccionConDestino):
    tipo = "mover"

    @staticmethod
    def _transferir(origen: Path, destino: Path) -> None:
        shutil.move(origen, destino)


@dataclass(frozen=True)
class AccionCopiar(_AccionConDestino):
    tipo = "copiar"

    @staticmethod
    def _transferir(origen: Path, destino: Path) -> None:
        shutil.copy2(origen, destino)


@dataclass(frozen=True)
class AccionRenombrar(Accion):
    """Renombra con una plantilla: {fecha:%Y-%m-%d}, {n:03}, {ext}, {nombre}, {slug}."""

    tipo = "renombrar"
    plantilla: str = ""

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {**super()._argumentos(datos), "plantilla": datos["plantilla"]}

    def nuevo_nombre(self, fichero: Path, n: int) -> str:
        return self.plantilla.format(
            fecha=datetime.fromtimestamp(fichero.stat().st_mtime),
            n=n,
            ext=fichero.suffix.lower(),
            nombre=fichero.stem,
            slug=slug(fichero.stem),
        )

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        ops = []
        reservados: set[Path] = set()
        for n, f in enumerate(ficheros, start=1):
            destino = f.with_name(self.nuevo_nombre(f, n))
            if destino == f:
                continue  # ya tiene el nombre correcto
            if destino in reservados:
                ops.append(Operacion(f, destino, omitida="otro fichero tendría el mismo nombre"))
            elif destino.exists() and not _mismo_fichero(f, destino):
                ops.append(Operacion(f, destino, omitida="ya existe un fichero con ese nombre"))
            else:
                ops.append(Operacion(f, destino))
            reservados.add(destino)
        return ops

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.destino is not None and operacion.omitida is None
        if operacion.destino.exists() and not _mismo_fichero(operacion.origen, operacion.destino):
            raise FileExistsError(f"ya existe {operacion.destino.name}")
        operacion.origen.rename(operacion.destino)


@dataclass(frozen=True)
class AccionBorrar(Accion):
    """Borra ficheros. Pide confirmación salvo que confirmar sea false o se pase --si."""

    tipo = "borrar"
    confirmar: bool = True

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {**super()._argumentos(datos), "confirmar": datos.get("confirmar", True)}

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        return [Operacion(f) for f in ficheros]

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.omitida is None
        operacion.origen.unlink()


@dataclass(frozen=True)
class AccionWebp(Accion):
    """Convierte imágenes a WebP, opcionalmente reduciendo su ancho (capturas y miniaturas)."""

    tipo = "webp"
    destino: str | None = None
    ancho_max: int | None = None
    calidad: int = 80

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {
            **super()._argumentos(datos),
            "destino": datos.get("destino"),
            "ancho_max": datos.get("ancho_max"),
            "calidad": datos.get("calidad", 80),
        }

    def carpeta_destino(self, carpeta: Path) -> Path:
        if not self.destino:
            return carpeta
        destino = Path(self.destino).expanduser()
        return destino if destino.is_absolute() else carpeta / destino

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        destino_dir = self.carpeta_destino(carpeta)
        ops = []
        for f in ficheros:
            destino = destino_dir / f"{slug(f.stem)}.webp"
            if destino.exists():
                ops.append(Operacion(f, destino, omitida="ya existe el .webp"))
            else:
                ops.append(Operacion(f, destino))
        return ops

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.destino is not None and operacion.omitida is None
        from PIL import Image, UnidentifiedImageError  # solo se carga si hace falta

        if operacion.destino.exists():
            raise FileExistsError(f"ya existe {operacion.destino.name}")
        operacion.destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(operacion.origen) as imagen:
                if self.ancho_max and imagen.width > self.ancho_max:
                    alto = round(imagen.height * self.ancho_max / imagen.width)
                    imagen = imagen.resize((self.ancho_max, alto), Image.Resampling.LANCZOS)
                if imagen.mode not in ("RGB", "RGBA"):
                    imagen = imagen.convert("RGBA")
                imagen.save(operacion.destino, "WEBP", quality=self.calidad, method=6)
        except UnidentifiedImageError:
            raise OSError("no es una imagen que se pueda abrir") from None


@dataclass(frozen=True)
class AccionInforme(Accion):
    """Lista los ficheros que cumplen el filtro (p. ej., demasiado pesados). No toca nada."""

    tipo = "informe"
    solo_lectura = True

    def planificar(self, ficheros: list[Path], carpeta: Path) -> list[Operacion]:
        ficheros = sorted(ficheros, key=lambda f: f.stat().st_size, reverse=True)
        return [Operacion(f, detalle=tamano_legible(f.stat().st_size)) for f in ficheros]

    def aplicar(self, operacion: Operacion) -> None:
        raise AssertionError("un informe no se aplica")


@dataclass(frozen=True)
class AccionCrear(Accion):
    """Crea un fichero nuevo copiando un modelo, con número siguiente y textos cambiados.

    Ejemplo: docs/prompts/plantilla.md → docs/prompts/19-tronker-en-discord.md
    """

    tipo = "crear"
    modelo: str = ""
    destino: str = ""
    nombre_fichero: str = ""
    reemplazar: tuple[tuple[str, str], ...] = ()

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {
            **super()._argumentos(datos),
            "modelo": datos["modelo"],
            "destino": datos["destino"],
            "nombre_fichero": datos["nombre_fichero"],
            "reemplazar": tuple(datos.get("reemplazar", {}).items()),
        }

    def preparar(self, carpeta: Path, ahora: datetime, texto: str | None) -> list[Operacion]:
        if not texto:
            raise ErrorUso(f"La acción {self.nombre} necesita un título: --texto \"...\"")
        modelo = _ruta_en(carpeta, self.modelo)
        if not modelo.is_file():
            raise ErrorUso(f"No encuentro el modelo {modelo}. ¿Estás en la carpeta del proyecto?")
        destino_dir = _ruta_en(carpeta, self.destino)
        nombre = self.nombre_fichero.format(
            n=siguiente_numero(destino_dir), fecha=ahora, texto=texto, slug=slug(texto)
        )
        destino = destino_dir / nombre
        if destino.exists():
            return [Operacion(modelo, destino, omitida="ya existe")]
        contenido = _leer_tal_cual(modelo)
        for viejo, nuevo in self.reemplazar:
            contenido = contenido.replace(viejo, nuevo.format(fecha=ahora, texto=texto), 1)
        return [Operacion(modelo, destino, detalle=f"desde {modelo.name}", contenido=contenido)]

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.destino is not None and operacion.contenido is not None
        operacion.destino.parent.mkdir(parents=True, exist_ok=True)
        with operacion.destino.open("x", encoding="utf-8", newline="") as f:  # "x": nunca sobrescribe
            f.write(operacion.contenido)


@dataclass(frozen=True)
class AccionIncrementar(Accion):
    """Suma 1 al número que captura «patron» dentro de «fichero» (p. ej., CACHE_VERSION de sw.js)."""

    tipo = "incrementar"
    fichero: str = ""
    patron: str = ""

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        return {**super()._argumentos(datos), "fichero": datos["fichero"], "patron": datos["patron"]}

    def preparar(self, carpeta: Path, ahora: datetime, texto: str | None) -> list[Operacion]:
        fichero = _ruta_en(carpeta, self.fichero)
        if not fichero.is_file():
            raise ErrorUso(f"No encuentro {fichero}. ¿Estás en la carpeta del proyecto?")
        encontrado = re.search(self.patron, _leer_tal_cual(fichero))
        if not encontrado:
            return [Operacion(fichero, omitida=f"no encuentro «{self.patron}» dentro")]
        actual = int(encontrado.group(1))
        return [Operacion(fichero, detalle=f"{encontrado.group(0)} → {actual + 1}")]

    def aplicar(self, operacion: Operacion) -> None:
        contenido = _leer_tal_cual(operacion.origen)
        encontrado = re.search(self.patron, contenido)
        if not encontrado:
            raise OSError("el número ya no está en el fichero")
        inicio, fin = encontrado.span(1)
        nuevo = contenido[:inicio] + str(int(encontrado.group(1)) + 1) + contenido[fin:]
        with operacion.origen.open("w", encoding="utf-8", newline="") as f:
            f.write(nuevo)


@dataclass(frozen=True)
class AccionComprimir(Accion):
    """Guarda la carpeta en un .zip con fecha. No entra en carpetas ocultas (.git, .venv…)."""

    tipo = "comprimir"
    destino: str = ""
    nombre_fichero: str = "{carpeta}-{fecha:%Y-%m-%d_%H%M}.zip"

    @classmethod
    def _argumentos(cls, datos: dict[str, Any]) -> dict[str, Any]:
        argumentos = {**super()._argumentos(datos), "destino": datos["destino"]}
        if "nombre_fichero" in datos:
            argumentos["nombre_fichero"] = datos["nombre_fichero"]
        return argumentos

    def preparar(self, carpeta: Path, ahora: datetime, texto: str | None) -> list[Operacion]:
        carpeta = carpeta.resolve()
        destino = _ruta_en(carpeta, self.destino) / self.nombre_fichero.format(
            carpeta=slug(carpeta.name), fecha=ahora
        )
        ficheros = self._ficheros(carpeta, destino)
        total = sum(f.stat().st_size for f in ficheros)
        if destino.exists():
            return [Operacion(carpeta, destino, omitida="ya existe esa copia")]
        return [Operacion(carpeta, destino, detalle=f"{len(ficheros)} ficheros, {tamano_legible(total)}")]

    def _ficheros(self, carpeta: Path, destino: Path) -> list[Path]:
        return [
            f
            for f in sorted(carpeta.rglob("*"))
            if f.is_file()
            and not f.is_symlink()
            and not any(p.startswith(".") for p in f.relative_to(carpeta).parts[:-1])
            and not f.resolve().is_relative_to(destino.parent.resolve())
        ]

    def aplicar(self, operacion: Operacion) -> None:
        assert operacion.destino is not None and operacion.omitida is None
        operacion.destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = operacion.destino.with_suffix(".zip.parcial")
        try:
            with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in self._ficheros(operacion.origen, operacion.destino):
                    zf.write(f, f.relative_to(operacion.origen).as_posix())
            temporal.rename(operacion.destino)
        finally:
            temporal.unlink(missing_ok=True)


def _ruta_en(carpeta: Path, ruta: str) -> Path:
    """Ruta del JSON: admite ~; si es relativa, se entiende dentro de la carpeta de trabajo."""
    ruta_p = Path(ruta).expanduser()
    return ruta_p if ruta_p.is_absolute() else carpeta / ruta_p


def _leer_tal_cual(fichero: Path) -> str:
    """Lee sin convertir saltos de línea, para no cambiar CRLF/LF al reescribir."""
    with fichero.open(encoding="utf-8", newline="") as f:
        return f.read()


def siguiente_numero(carpeta: Path) -> int:
    """1 + el mayor número con el que empieza un fichero de la carpeta (18-x.md → 19)."""
    numeros = [
        int(m.group(1))
        for f in (carpeta.iterdir() if carpeta.is_dir() else [])
        if (m := re.match(r"(\d+)", f.name))
    ]
    return max(numeros, default=0) + 1


def tamano_legible(n: float) -> str:
    if n < 1024:
        return f"{n:.0f} B"
    for unidad in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024 or unidad == "GB":
            break
    return f"{n:.1f} {unidad}"


def slug(texto: str) -> str:
    """«Captura Tronk Fight (2)» → «captura-tronk-fight-2»: sin tildes, espacios ni mayúsculas."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-") or "fichero"


def _mismo_fichero(a: Path, b: Path) -> bool:
    """True si a y b son el mismo fichero (p. ej., «Foto.JPG» y «foto.jpg» en Windows o macOS)."""
    try:
        return a.samefile(b)
    except OSError:
        return False


TIPOS: dict[str, type[Accion]] = {
    clase.tipo: clase for clase in (
        AccionMover,
        AccionCopiar,
        AccionRenombrar,
        AccionBorrar,
        AccionWebp,
        AccionInforme,
        AccionCrear,
        AccionIncrementar,
        AccionComprimir,
    )
}
