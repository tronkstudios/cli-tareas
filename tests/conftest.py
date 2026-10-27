import json
from pathlib import Path

import pytest


@pytest.fixture
def escribir_config(tmp_path: Path):
    """Escribe un acciones.json con las acciones dadas y devuelve su ruta."""

    def _escribir(*acciones: dict, version: int = 1) -> Path:
        ruta = tmp_path / "acciones.json"
        ruta.write_text(
            json.dumps({"version": version, "acciones": list(acciones)}, ensure_ascii=False),
            encoding="utf-8",
        )
        return ruta

    return _escribir
