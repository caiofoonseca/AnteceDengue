import json
from pathlib import Path

from src import config

NOTEBOOK = config.ROOT / "notebooks" / "01_eda.ipynb"


def load():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def test_notebook_executado_sem_erros():
    codigo = [c for c in load() if c["cell_type"] == "code"]
    assert codigo
    assert all(c["execution_count"] is not None for c in codigo)
    erros = [o for c in codigo for o in c["outputs"] if o["output_type"] == "error"]
    assert erros == []


def test_notebook_tem_figuras_e_interpretacao():
    figuras = list((config.REPORTS_DIR / "figuras").glob("eda_*.png"))
    assert len(figuras) >= 8
    texto = "\n".join("".join(c["source"]) for c in load() if c["cell_type"] == "markdown")
    assert "a preencher" not in texto
    assert texto.count("**Interpretação.**") >= 15


def test_notebook_nao_toca_no_teste():
    codigo = "\n".join("".join(c["source"]) for c in load() if c["cell_type"] == "code")
    assert "split.test" not in codigo
    assert "locked_split" in codigo
