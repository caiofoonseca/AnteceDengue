import json

import joblib
import numpy as np
import pytest

from src import config
from src.features import build_features, feature_columns
from src.final import (META_FIELDS, FinalAlreadyEvaluated, block_bootstrap, f1_macro_from_cm, run_final,
                       week_confusions)
from src.search import choose_final, run_exp03
from src.tracking import Tracker
from src.train import locked_split
from tests.conftest import make_clima, make_panel


@pytest.fixture(scope="module")
def df():
    return build_features(make_panel(n_weeks=170, bairros=("A", "B", "C")), make_clima(170), city=True)


@pytest.fixture(scope="module")
def pronto(df, tmp_path_factory):
    base = tmp_path_factory.mktemp("exp03")
    choice_path = base / "modelo_escolhido.json"
    run_exp03(df, Tracker("x", enabled=False), 3, base, base / "fig", choice_path, models_to_tune=("logreg", "rf"))
    return base, choice_path


def caminhos(base, choice_path):
    return dict(choice_path=choice_path, final_path=base / "teste_final.json", model_path=base / "m.joblib",
                meta_path=base / "meta.json", reports_dir=base, figures_dir=base / "fig", resamples=50)


def test_escolha_gravada(pronto):
    _, choice_path = pronto
    escolha = json.loads(choice_path.read_text(encoding="utf-8"))
    assert escolha["name"] in ("logreg", "rf")
    assert escolha["conjunto_features"] in ("base", "base+cidade")
    assert escolha["features"]


def test_avaliacao_final_recusa_rodar_duas_vezes(df, pronto):
    base, choice_path = pronto
    kw = caminhos(base, choice_path)
    run_final(df, Tracker("x", enabled=False), **kw)
    assert kw["final_path"].exists()
    with pytest.raises(FinalAlreadyEvaluated, match="invalida"):
        run_final(df, Tracker("x", enabled=False), **kw)
    run_final(df, Tracker("x", enabled=False), force_reeval=True, **kw)


def test_meta_tem_todos_os_campos_e_modelo_preve(df, pronto):
    base, choice_path = pronto
    kw = caminhos(base, choice_path)
    if not kw["final_path"].exists():
        run_final(df, Tracker("x", enabled=False), **kw)
    meta = json.loads(kw["meta_path"].read_text(encoding="utf-8"))
    for campo in META_FIELDS:
        assert campo in meta, campo
    assert meta["classes"] == config.CLASSES
    modelo = joblib.load(kw["model_path"])
    X = df[meta["features"]].head(40)
    assert set(modelo.predict(X)) <= {0, 1, 2}
    assert list(modelo.feature_names_in_) == meta["features"]


def test_registry_com_alias_champion(df, pronto, tmp_path, monkeypatch):
    mlflow = pytest.importorskip("mlflow")
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    monkeypatch.setenv("MLFLOW_ARTIFACT_ROOT", str(tmp_path))
    base, choice_path = pronto
    kw = caminhos(tmp_path, choice_path)
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    run_final(df, Tracker("exp-teste"), **kw)
    from mlflow.tracking import MlflowClient

    versao = MlflowClient().get_model_version_by_alias(config.MLFLOW_MODEL_NAME, config.CHAMPION_ALIAS)
    assert versao.name == config.MLFLOW_MODEL_NAME
    assert versao.run_id


def test_bootstrap_identico_da_diferenca_zero():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 3, 200)
    semanas = np.repeat(np.arange(20), 10)
    cm = week_confusions(y, y, semanas, np.arange(20))
    b = block_bootstrap(cm, cm, 4, 100, 1)
    assert b["f1_diff_ci95"] == [0.0, 0.0]
    assert f1_macro_from_cm(cm.sum(axis=0)) == pytest.approx(1.0)


def test_choose_final_prefere_maior_cv():
    a = {"display": "A", "cv_f1_media_f2_5": 0.5, "val_f1_macro": 0.5}
    b = {"display": "B", "cv_f1_media_f2_5": 0.4, "val_f1_macro": 0.6}
    r = choose_final([a, b], 0.3)
    assert r["display"] == "A"
    assert r["validacao_confirma"] is False


def test_teste_continua_bloqueado_na_busca(df):
    from src.train import TestSetLocked

    with pytest.raises(TestSetLocked):
        locked_split(df).test
