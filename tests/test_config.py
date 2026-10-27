import json
from pathlib import Path

import pytest

from tareas.config import Configuracion, validar
from tareas.errores import AccionNoEncontrada, ConfigError

REPO = Path(__file__).parent.parent


def test_el_acciones_json_del_repo_es_valido():
    conf = Configuracion.desde_fichero(REPO / "acciones.json")
    assert len(conf.acciones) >= 5


def test_dice_que_campo_falla():
    errores = validar(
        {"version": 1, "acciones": [{"nombre": "x", "descripcion": "d", "tipo": "mover"}]}
    )
    assert errores == ["acciones[0] (x).destino: obligatorio para el tipo mover"]


def test_nombres_repetidos_y_tipo_desconocido():
    accion = {"nombre": "a", "descripcion": "d", "tipo": "borrar"}
    errores = validar({"version": 1, "acciones": [accion, accion, {**accion, "nombre": "b", "tipo": "volar"}]})
    assert any("está repetido" in e for e in errores)
    assert any("'volar' no es válido" in e for e in errores)


def test_json_roto_da_config_error_con_linea(tmp_path):
    ruta = tmp_path / "acciones.json"
    ruta.write_text('{"version": 1,', encoding="utf-8")
    with pytest.raises(ConfigError, match="línea 1"):
        Configuracion.desde_fichero(ruta)


def test_fichero_que_no_existe(tmp_path):
    with pytest.raises(ConfigError, match="No encuentro"):
        Configuracion.desde_fichero(tmp_path / "nada.json")


def test_accion_que_no_existe(escribir_config):
    ruta = escribir_config({"nombre": "a", "descripcion": "d", "tipo": "borrar"})
    with pytest.raises(AccionNoEncontrada, match="Disponibles: a"):
        Configuracion.desde_fichero(ruta).buscar("b")


def test_plantilla_con_variable_desconocida():
    errores = validar({"version": 1, "acciones": [
        {"nombre": "r", "descripcion": "d", "tipo": "renombrar", "plantilla": "{fechas}{ext}"}
    ]})
    assert errores and "variable desconocida" in errores[0]
