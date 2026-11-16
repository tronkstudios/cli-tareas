"""Capa de IA sin red real: un proveedor falso y un servidor HTTP local de mentira."""

import json
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import platformdirs
import pytest
from typer.testing import CliRunner

from tareas.acciones import Accion
from tareas.cli import app
from tareas.config import validar
from tareas.errores import ErrorUso, IASinConexion, IASinConfigurar
from tareas.ia import ProveedorIA, ProveedorOpenAI
from tareas.motor import Motor

CLAVE = "sk-clave-secreta-de-prueba"
runner = CliRunner()


class ProveedorFalso(ProveedorIA):
    """Contesta sin red y apunta cada llamada."""

    def __init__(self):
        self.llamadas: list[tuple[str, str]] = []

    def completar(self, instrucciones: str, texto: str) -> str:
        self.llamadas.append((instrucciones, texto))
        return f"RESUMEN de {len(texto)} caracteres"

    def describir(self) -> str:
        return "falso"


def _accion(**datos) -> Accion:
    return Accion.desde_dict({"nombre": "prueba", "descripcion": "d", "instrucciones": "Resume", "tipo": "ia", **datos})


@pytest.fixture
def sin_configuracion(monkeypatch, tmp_path):
    """Ni variables de entorno ni .env (tampoco el del usuario)."""
    for variable in ("TAREAS_IA_URL", "TAREAS_IA_MODELO", "TAREAS_IA_CLAVE", "TAREAS_IA_CA"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(platformdirs, "user_config_path", lambda *a, **k: tmp_path / "usuario")
    monkeypatch.chdir(tmp_path)


# --- Proveedor ---------------------------------------------------------------


def test_sin_variables_es_ia_sin_configurar(sin_configuracion):
    with pytest.raises(IASinConfigurar, match="TAREAS_IA_URL"):
        ProveedorIA.desde_entorno()


def test_lee_el_env_de_la_carpeta_actual(sin_configuracion, tmp_path):
    (tmp_path / ".env").write_text(
        f"TAREAS_IA_URL=http://127.0.0.1:9/v1\nTAREAS_IA_MODELO=modelo-x\nTAREAS_IA_CLAVE={CLAVE}\n",
        encoding="utf-8",
    )
    proveedor = ProveedorIA.desde_entorno()
    assert proveedor.describir() == "modelo-x en http://127.0.0.1:9/v1/chat/completions"
    assert CLAVE not in repr(proveedor)


class _Servidor(BaseHTTPRequestHandler):
    """Servidor de mentira: el modelo decide la respuesta."""

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).recibido = {"cuerpo": cuerpo, "autorizacion": self.headers["Authorization"]}
        modelo = cuerpo["model"]
        if modelo == "caido":
            self._responder(503, b"<h1>503 Service Unavailable</h1>")
        elif modelo == "sin-permiso":
            self._responder(401, b'{"error": "bad key"}')
        elif modelo == "roto":
            self._responder(200, b"esto no es json")
        else:
            respuesta = {"choices": [{"message": {"content": "<think>pienso…</think>\n  Hola  "}}]}
            self._responder(200, json.dumps(respuesta).encode())

    def _responder(self, codigo: int, cuerpo: bytes):
        self.send_response(codigo)
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):  # sin ruido en la salida de pytest
        pass


@pytest.fixture(scope="module")
def servidor():
    httpd = HTTPServer(("127.0.0.1", 0), _Servidor)
    hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1"
    httpd.shutdown()


def test_respuesta_correcta_sin_el_pensamiento(servidor):
    proveedor = ProveedorOpenAI(servidor, "bueno", CLAVE)
    assert proveedor.completar("Saluda", "hola") == "Hola"
    assert _Servidor.recibido["autorizacion"] == f"Bearer {CLAVE}"
    assert [m["role"] for m in _Servidor.recibido["cuerpo"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize(
    ("modelo", "error", "texto"),
    [
        ("caido", IASinConexion, "no está disponible"),
        ("sin-permiso", IASinConfigurar, "rechaza la clave"),
        ("roto", IASinConexion, "no es JSON"),
    ],
)
def test_errores_del_servidor_con_mensaje_humano_y_sin_la_clave(servidor, modelo, error, texto):
    with pytest.raises(error, match=texto) as e:
        ProveedorOpenAI(servidor, modelo, CLAVE).completar("x", "y")
    assert CLAVE not in str(e.value)


def test_sin_conexion(servidor):
    with socket.socket() as s:  # un puerto libre en el que no escucha nadie
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    with pytest.raises(IASinConexion, match="No hay conexión"):
        ProveedorOpenAI(f"http://127.0.0.1:{puerto}/v1", "m", CLAVE, espera=5).completar("x", "y")


# --- Acción «ia» ---------------------------------------------------------------


def test_simular_no_llama_al_modelo(tmp_path: Path):
    (tmp_path / "notas.md").write_text("Apuntes largos", encoding="utf-8")
    plan = Motor().planificar(_accion(salida="{nombre}.resumen.md"), tmp_path)
    assert [op.origen.name for op in plan.pendientes] == ["notas.md"]
    assert not (tmp_path / "notas.resumen.md").exists()


def test_ficheros_crea_respuestas_y_no_se_resume_a_si_misma(tmp_path: Path):
    (tmp_path / "a.md").write_text("Texto A", encoding="utf-8")
    (tmp_path / "b.md").write_text("Texto B", encoding="utf-8")
    (tmp_path / "b.resumen.md").write_text("ya estaba", encoding="utf-8")
    (tmp_path / "foto.png").write_bytes(b"\x89PNG\x00\xff")
    proveedor = ProveedorFalso()
    plan = Motor().planificar(_accion(salida="{nombre}.resumen.md"), tmp_path)

    assert {op.origen.name: op.omitida for op in plan.operaciones} == {
        "a.md": None,
        "b.md": "ya existe la respuesta",
        "foto.png": "no es un fichero de texto UTF-8",
    }
    resultado = Motor.ejecutar(plan, proveedor)
    assert resultado.ok and proveedor.llamadas == [("Resume", "Texto A")]
    assert (tmp_path / "a.resumen.md").read_text(encoding="utf-8") == "RESUMEN de 7 caracteres\n"
    assert (tmp_path / "b.resumen.md").read_text(encoding="utf-8") == "ya estaba"


def test_recorta_textos_largos(tmp_path: Path):
    (tmp_path / "largo.txt").write_text("x" * 500, encoding="utf-8")
    plan = Motor().planificar(_accion(max_caracteres=100), tmp_path)
    assert "recortado de 500" in plan.operaciones[0].detalle
    proveedor = ProveedorFalso()
    Motor.ejecutar(plan, proveedor)
    assert len(proveedor.llamadas[0][1]) == 100


def test_sin_salida_la_respuesta_vuelve_para_la_pantalla(tmp_path: Path):
    (tmp_path / "a.txt").write_text("hola", encoding="utf-8")
    resultado = Motor.ejecutar(Motor().planificar(_accion(), tmp_path), ProveedorFalso())
    assert [r for _, r in resultado.respuestas] == ["RESUMEN de 4 caracteres"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.txt"]


def _repo(carpeta: Path) -> Path:
    def git(*args):
        subprocess.run(["git", "-C", str(carpeta), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True,
                       capture_output=True)

    git("init", "-q")
    (carpeta / "a.txt").write_text("uno\n", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-q", "-m", "Primer commit: añade a.txt")
    return carpeta


def test_git_log_manda_los_commits(tmp_path: Path):
    _repo(tmp_path)
    proveedor = ProveedorFalso()
    plan = Motor().planificar(_accion(entrada="git-log", salida="cambios.md"), tmp_path)
    Motor.ejecutar(plan, proveedor)
    assert "Primer commit: añade a.txt" in proveedor.llamadas[0][1]
    assert (tmp_path / "cambios.md").exists()


def test_git_diff_sin_cambios_se_omite_y_con_cambios_se_manda(tmp_path: Path):
    _repo(tmp_path)
    accion = _accion(entrada="git-diff")
    assert Motor().planificar(accion, tmp_path).omitidas[0].omitida == "no hay cambios sin commitear"
    (tmp_path / "a.txt").write_text("dos\n", encoding="utf-8")
    assert "+dos" in Motor().planificar(accion, tmp_path).pendientes[0].contenido


def test_git_fuera_de_un_repo_es_error_de_uso(tmp_path: Path):
    with pytest.raises(ErrorUso, match="no es un repositorio git"):
        Motor().planificar(_accion(entrada="git-log"), tmp_path)


def test_validacion_de_la_accion_ia():
    errores = validar({"version": 1, "acciones": [
        {"nombre": "x", "descripcion": "d", "tipo": "ia", "entrada": "web", "commits": 0, "salida": "../fuera.md"}
    ]})
    assert any("instrucciones: obligatorio" in e for e in errores)
    assert any("entrada: 'web' no es válida" in e for e in errores)
    assert any("commits: debe ser un entero" in e for e in errores)
    assert any("no puede usar «..»" in e for e in errores)


# --- Interfaz y modo sin red ----------------------------------------------------


def _config(tmp_path: Path) -> Path:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(json.dumps({"version": 1, "acciones": [
        {"nombre": "resumir", "descripcion": "d", "tipo": "ia", "instrucciones": "Resume"},
        {"nombre": "limpiar", "descripcion": "d", "tipo": "borrar", "filtro": {"patron": r"\.tmp$"}},
    ]}), encoding="utf-8")
    return ruta


def test_comprobar_ia_sin_configurar(sin_configuracion):
    resultado = runner.invoke(app, ["comprobar-ia"])
    assert resultado.exit_code == 1
    assert "Falta configurar" in resultado.output and "Traceback" not in resultado.output


def test_sin_red_la_accion_ia_falla_en_una_linea_y_las_demas_siguen(sin_configuracion, tmp_path, monkeypatch):
    monkeypatch.setenv("TAREAS_IA_URL", "http://127.0.0.1:9/v1")  # nadie escucha ahí
    monkeypatch.setenv("TAREAS_IA_MODELO", "m")
    monkeypatch.setenv("TAREAS_IA_CLAVE", CLAVE)
    monkeypatch.setenv("TAREAS_IA_ESPERA", "5")
    config = _config(tmp_path)
    (tmp_path / "datos").mkdir()
    (tmp_path / "datos" / "nota.txt").write_text("hola", encoding="utf-8")
    (tmp_path / "datos" / "x.tmp").write_text("x", encoding="utf-8")

    ia = runner.invoke(app, ["-c", str(config), "ejecutar", "resumir", str(tmp_path / "datos")])
    assert ia.exit_code == 1 and "No hay conexión" in ia.output
    assert CLAVE not in ia.output and "Traceback" not in ia.output

    normal = runner.invoke(app, ["-c", str(config), "ejecutar", "limpiar", str(tmp_path / "datos"), "--si"])
    assert normal.exit_code == 0 and not (tmp_path / "datos" / "x.tmp").exists()


def test_acciones_marca_las_de_ia(tmp_path):
    resultado = runner.invoke(app, ["-c", str(_config(tmp_path)), "acciones", "--json"])
    assert {a["nombre"]: a["ia"] for a in json.loads(resultado.output)} == {"resumir": True, "limpiar": False}
