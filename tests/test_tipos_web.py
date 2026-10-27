"""Tipos pensados para la web de Tronk Studios: crear, incrementar, informe y comprimir."""

import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from tareas.acciones import Accion
from tareas.errores import ErrorUso
from tareas.motor import Motor

AHORA = datetime(2026, 10, 27, 16, 30)


def _accion(**datos) -> Accion:
    return Accion.desde_dict({"nombre": "prueba", "descripcion": "d", **datos})


def _hacer(accion: Accion, carpeta: Path, texto: str | None = None):
    plan = Motor(AHORA).planificar(accion, carpeta, texto)
    return plan, Motor.ejecutar(plan)


@pytest.fixture
def web(tmp_path: Path) -> Path:
    prompts = tmp_path / "docs" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "plantilla.md").write_text("# Título del prompt\n\n- **Fecha:**\n", encoding="utf-8")
    (prompts / "05-plataforma.md").write_text("x", encoding="utf-8")
    (prompts / "18-rendimiento.md").write_text("x", encoding="utf-8")
    (tmp_path / "sw.js").write_bytes(b"// cache\r\nconst CACHE_VERSION = 6;\r\n")
    return tmp_path


NUEVO_PROMPT = dict(
    tipo="crear",
    modelo="docs/prompts/plantilla.md",
    destino="docs/prompts",
    nombre_fichero="{n:02}-{slug}.md",
    reemplazar={"# Título del prompt": "# {texto}", "- **Fecha:**": "- **Fecha:** {fecha:%d/%m/%Y}"},
)


def test_crear_usa_el_numero_siguiente_y_rellena_la_plantilla(web: Path):
    _, resultado = _hacer(_accion(**NUEVO_PROMPT), web, "Tronker en Discord")
    assert resultado.ok
    nuevo = web / "docs" / "prompts" / "19-tronker-en-discord.md"
    assert nuevo.read_text(encoding="utf-8") == "# Tronker en Discord\n\n- **Fecha:** 27/10/2026\n"


def test_crear_sin_texto_es_error_de_uso(web: Path):
    with pytest.raises(ErrorUso, match="--texto"):
        Motor(AHORA).planificar(_accion(**NUEVO_PROMPT), web)


def test_crear_fuera_del_proyecto_es_error_de_uso(tmp_path: Path):
    with pytest.raises(ErrorUso, match="modelo"):
        Motor(AHORA).planificar(_accion(**NUEVO_PROMPT), tmp_path, "Algo")


def test_incrementar_cambia_solo_el_numero_y_respeta_crlf(web: Path):
    accion = _accion(tipo="incrementar", fichero="sw.js", patron=r"const CACHE_VERSION = (\d+);")
    plan, resultado = _hacer(accion, web)
    assert resultado.ok and "→ 7" in plan.operaciones[0].detalle
    assert (web / "sw.js").read_bytes() == b"// cache\r\nconst CACHE_VERSION = 7;\r\n"


def test_incrementar_sin_coincidencia_se_omite(web: Path):
    accion = _accion(tipo="incrementar", fichero="sw.js", patron=r"VERSION_QUE_NO_EXISTE = (\d+)")
    plan = Motor(AHORA).planificar(accion, web)
    assert plan.pendientes == [] and len(plan.omitidas) == 1


def test_informe_lista_lo_pesado_sin_tocar_nada(tmp_path: Path):
    (tmp_path / "grande.webp").write_bytes(b"x" * 300 * 1024)
    (tmp_path / "pequena.webp").write_bytes(b"x" * 10)
    accion = _accion(tipo="informe", filtro={"mas_grande_que_kb": 200})
    plan = Motor(AHORA).planificar(accion, tmp_path)
    assert [op.origen.name for op in plan.operaciones] == ["grande.webp"]
    assert plan.operaciones[0].detalle == "300.0 KB"


def test_comprimir_sin_git_y_sin_meterse_a_si_misma(web: Path):
    (web / ".git").mkdir()
    (web / ".git" / "config").write_text("x", encoding="utf-8")
    (web / ".gitignore").write_text(".env\n", encoding="utf-8")
    accion = _accion(tipo="comprimir", destino="copias")
    plan, resultado = _hacer(accion, web)
    assert resultado.ok
    [zip_creado] = (web / "copias").iterdir()
    assert zip_creado.name == f"{web.name.lower().replace('_', '-')}-2026-10-27_1630.zip"
    nombres = zipfile.ZipFile(zip_creado).namelist()
    assert "sw.js" in nombres and ".gitignore" in nombres
    assert not any(n.startswith((".git/", "copias/")) for n in nombres)
