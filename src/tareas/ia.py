"""Proveedor de IA: manda instrucciones y un texto a un modelo y devuelve su respuesta.

Solo se importa cuando una acción de tipo «ia» o «tareas comprobar-ia» lo necesita:
sin red o sin configuración, el resto de la herramienta funciona igual.
"""

import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

from tareas.errores import IASinConexion, IASinConfigurar

VARIABLES = ("TAREAS_IA_URL", "TAREAS_IA_MODELO", "TAREAS_IA_CLAVE")
_PENSAMIENTO = re.compile(r"<think>.*?</think>", re.DOTALL)


class ProveedorIA(ABC):
    """Cualquier modelo que sepa completar: el resto del código solo conoce esta clase."""

    @abstractmethod
    def completar(self, instrucciones: str, texto: str) -> str:
        """Devuelve la respuesta del modelo. Lanza IAError si no puede."""

    @abstractmethod
    def describir(self) -> str:
        """Texto para enseñar a la persona qué modelo se usa (nunca la clave)."""

    @staticmethod
    def desde_entorno() -> "ProveedorIA":
        """Fábrica: crea el proveedor con las variables de entorno (o un .env).

        Busca .env en la carpeta actual y en la carpeta de configuración del usuario.
        Las variables que ya existen mandan sobre el .env.
        """
        _cargar_env()
        faltan = [v for v in VARIABLES if not os.environ.get(v, "").strip()]
        if faltan:
            raise IASinConfigurar(
                f"Falta configurar {', '.join(faltan)} (mira .env.example). "
                "Las acciones sin IA siguen disponibles."
            )
        ca = os.environ.get("TAREAS_IA_CA", "").strip() or None
        if ca and not Path(ca).expanduser().is_file():
            raise IASinConfigurar(f"TAREAS_IA_CA apunta a {ca}, que no existe.")
        return ProveedorOpenAI(
            url=os.environ["TAREAS_IA_URL"].strip(),
            modelo=os.environ["TAREAS_IA_MODELO"].strip(),
            clave=os.environ["TAREAS_IA_CLAVE"].strip(),
            ca=Path(ca).expanduser() if ca else None,
            espera=float(os.environ.get("TAREAS_IA_ESPERA", "180")),
        )


class ProveedorOpenAI(ProveedorIA):
    """API compatible con OpenAI (/chat/completions): la de los modelos del centro,
    LiteLLM, vLLM, Ollama… Usa solo la librería estándar."""

    def __init__(self, url: str, modelo: str, clave: str, ca: Path | None = None, espera: float = 180):
        self._url = url.rstrip("/") + "/chat/completions"
        self._modelo = modelo
        self.__clave = clave  # privada: no sale en mensajes ni en repr
        self._espera = espera
        # Certificado propio del centro: se añade a los de confianza, nunca se desactiva la verificación.
        self._ssl = ssl.create_default_context(cafile=str(ca) if ca else None)

    def __repr__(self) -> str:
        return f"ProveedorOpenAI({self.describir()})"

    def describir(self) -> str:
        return f"{self._modelo} en {self._url}"

    def completar(self, instrucciones: str, texto: str) -> str:
        cuerpo = json.dumps(
            {
                "model": self._modelo,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": instrucciones},
                    {"role": "user", "content": texto},
                ],
            }
        ).encode("utf-8")
        peticion = urllib.request.Request(
            self._url,
            data=cuerpo,
            headers={
                "Authorization": f"Bearer {self.__clave}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self._espera, context=self._ssl) as r:
                datos = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise _error_http(e.code, self._modelo) from None
        except urllib.error.URLError as e:
            motivo = e.reason
            if isinstance(motivo, ssl.SSLCertVerificationError):
                raise IASinConexion(
                    "El certificado del servidor no es de confianza: indica el del centro "
                    "en TAREAS_IA_CA."
                ) from None
            if isinstance(motivo, (TimeoutError, socket.timeout)):
                raise _sin_tiempo(self._espera) from None
            raise IASinConexion(
                f"No hay conexión con el modelo ({motivo}). Las acciones sin IA siguen disponibles."
            ) from None
        except (TimeoutError, socket.timeout):
            raise _sin_tiempo(self._espera) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise IASinConexion("El servidor de IA ha respondido algo que no es JSON.") from None

        try:
            contenido = datos["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise IASinConexion("La respuesta del modelo no tiene el formato esperado.") from None
        contenido = _PENSAMIENTO.sub("", contenido).strip()
        if not contenido:
            raise IASinConexion("El modelo ha devuelto una respuesta vacía.")
        return contenido


def _error_http(codigo: int, modelo: str) -> Exception:
    if codigo in (401, 403):
        return IASinConfigurar(f"El servidor de IA rechaza la clave (HTTP {codigo}): revisa TAREAS_IA_CLAVE.")
    if codigo == 404:
        return IASinConfigurar(
            f"El servidor no encuentra la API o el modelo «{modelo}» (HTTP 404): revisa "
            "TAREAS_IA_URL (suele acabar en /v1) y TAREAS_IA_MODELO."
        )
    if codigo in (502, 503, 504):
        return IASinConexion(
            f"El modelo «{modelo}» no está disponible ahora mismo (HTTP {codigo}). "
            "Prueba otro modelo o más tarde."
        )
    return IASinConexion(f"El servidor de IA ha respondido con un error (HTTP {codigo}).")


def _sin_tiempo(espera: float) -> IASinConexion:
    return IASinConexion(
        f"El modelo no ha respondido en {espera:.0f} s. Sube TAREAS_IA_ESPERA o prueba más tarde."
    )


def _cargar_env() -> None:
    from dotenv import load_dotenv
    from platformdirs import user_config_path

    for env in (Path.cwd() / ".env", user_config_path("tareas") / ".env"):
        if env.is_file():
            load_dotenv(env, override=False, encoding="utf-8")
