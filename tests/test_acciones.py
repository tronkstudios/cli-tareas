from pathlib import Path

from PIL import Image

from tareas.acciones import Accion, slug
from tareas.motor import Motor


def _accion(**datos) -> Accion:
    return Accion.desde_dict({"nombre": "prueba", "descripcion": "d", **datos})


def test_slug_quita_tildes_espacios_y_mayusculas():
    assert slug("Captura Física (2)") == "captura-fisica-2"
    assert slug("¡¡!!") == "fichero"


def test_simular_no_toca_nada(tmp_path: Path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    accion = _accion(tipo="mover", destino="docs", filtro={"extensiones": [".PDF"]})
    plan = Motor().planificar(accion, tmp_path)
    assert [op.origen.name for op in plan.pendientes] == ["a.pdf"]
    assert (tmp_path / "a.pdf").exists() and not (tmp_path / "docs").exists()


def test_mover_no_sobrescribe(tmp_path: Path):
    (tmp_path / "a.mp4").write_text("nuevo", encoding="utf-8")
    (tmp_path / "video").mkdir()
    (tmp_path / "video" / "a.mp4").write_text("viejo", encoding="utf-8")
    accion = _accion(tipo="mover", destino="video")
    plan = Motor().planificar(accion, tmp_path)
    assert plan.pendientes == [] and len(plan.omitidas) == 1
    Motor.ejecutar(plan)
    assert (tmp_path / "video" / "a.mp4").read_text(encoding="utf-8") == "viejo"


def test_renombrar_con_slug(tmp_path: Path):
    (tmp_path / "Captura Tronk Fight.PNG").write_bytes(b"x")
    (tmp_path / ".DS_Store").write_bytes(b"x")
    accion = _accion(tipo="renombrar", plantilla="{slug}{ext}")
    resultado = Motor.ejecutar(Motor().planificar(accion, tmp_path))
    assert resultado.ok
    assert sorted(p.name for p in tmp_path.iterdir()) == [".DS_Store", "captura-tronk-fight.png"]


def test_borrar_recursivo_no_entra_en_git(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "a.tmp").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.tmp").write_bytes(b"x")
    accion = _accion(tipo="borrar", filtro={"patron": r"\.tmp$", "recursivo": True})
    assert accion.confirmar is True
    Motor.ejecutar(Motor().planificar(accion, tmp_path))
    assert (tmp_path / ".git" / "a.tmp").exists()
    assert not (tmp_path / "sub" / "b.tmp").exists()


def test_webp_reduce_el_ancho(tmp_path: Path):
    Image.new("RGB", (2000, 1000), "red").save(tmp_path / "Captura Uno.png")
    accion = _accion(tipo="webp", destino="mini", ancho_max=480)
    resultado = Motor.ejecutar(Motor().planificar(accion, tmp_path))
    assert resultado.ok
    with Image.open(tmp_path / "mini" / "captura-uno.webp") as imagen:
        assert imagen.size == (480, 240)


def test_webp_con_fichero_que_no_es_imagen_no_revienta(tmp_path: Path):
    (tmp_path / "falsa.png").write_text("no soy una imagen", encoding="utf-8")
    resultado = Motor.ejecutar(Motor().planificar(_accion(tipo="webp"), tmp_path))
    assert not resultado.ok and "imagen" in resultado.fallos[0][1]
