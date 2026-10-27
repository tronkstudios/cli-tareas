import json
from pathlib import Path

from typer.testing import CliRunner

from tareas import __version__
from tareas.cli import app

runner = CliRunner()


def test_version():
    resultado = runner.invoke(app, ["version"])
    assert resultado.exit_code == 0 and __version__ in resultado.output


def test_listar_json(tmp_path: Path):
    (tmp_path / "Apuntes de Física.pdf").write_bytes(b"12345")
    resultado = runner.invoke(app, ["listar", str(tmp_path), "--json"])
    assert resultado.exit_code == 0
    [fila] = json.loads(resultado.output)
    assert (fila["nombre"], fila["tipo"], fila["tamano_bytes"]) == ("Apuntes de Física.pdf", "pdf", 5)


def test_listar_carpeta_que_no_existe(tmp_path: Path):
    resultado = runner.invoke(app, ["listar", str(tmp_path / "nada")])
    assert resultado.exit_code == 2


def test_validar_invalido_sale_con_3(escribir_config):
    ruta = escribir_config({"nombre": "a", "tipo": "mover"})
    resultado = runner.invoke(app, ["--config", str(ruta), "validar"])
    assert resultado.exit_code == 3
    assert "descripcion" in resultado.output


def test_ejecutar_simular_y_de_verdad(escribir_config, tmp_path: Path):
    ruta = escribir_config(
        {"nombre": "limpiar", "descripcion": "d", "tipo": "borrar", "filtro": {"patron": r"\.tmp$"}}
    )
    (tmp_path / "a.tmp").write_bytes(b"x")

    simulado = runner.invoke(app, ["-c", str(ruta), "ejecutar", "limpiar", str(tmp_path), "--simular"])
    assert simulado.exit_code == 0 and (tmp_path / "a.tmp").exists()

    # Sin terminal (como en un script) y sin --si: se niega a borrar.
    sin_si = runner.invoke(app, ["-c", str(ruta), "ejecutar", "limpiar", str(tmp_path)])
    assert sin_si.exit_code == 2 and (tmp_path / "a.tmp").exists()

    con_si = runner.invoke(app, ["-c", str(ruta), "ejecutar", "limpiar", str(tmp_path), "--si"])
    assert con_si.exit_code == 0 and not (tmp_path / "a.tmp").exists()
