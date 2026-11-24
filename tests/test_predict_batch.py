import json

import joblib
import numpy as np
import pandas as pd
import pytest

from src import config
from src.features import build_features, feature_columns
from src.labels import apply_thresholds
from src.models import build_model
from src.predict_batch import FeatureMismatch, OUTPUT_COLUMNS, predict_latest, run, select_features
from tests.conftest import make_clima, make_panel

BAIRROS = tuple(f"B{i:02d}" for i in range(94))


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    base = tmp_path_factory.mktemp("batch")
    panel, clima = make_panel(n_weeks=45, bairros=BAIRROS), make_clima(45)
    df = build_features(panel, clima, city=True)
    y = apply_thresholds(df["target_casos"], (1.0, 4.0))
    features = feature_columns(True)
    modelo = build_model("rf", {"clf__n_estimators": 20}).fit(df[features], y)
    meta = {"sklearn_version": __import__("sklearn").__version__, "model_name": "RandomForest", "features": features}
    joblib.dump(modelo, base / "m.joblib")
    (base / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return base, modelo, meta, panel, clima


def test_saida_formato_e_invariantes(ambiente):
    _, modelo, meta, panel, clima = ambiente
    out = predict_latest(modelo, meta, panel, clima)
    assert list(out.columns) == OUTPUT_COLUMNS
    assert len(out) == 94 and out["bairro"].is_unique
    assert np.allclose(out[["prob_baixo", "prob_medio", "prob_alto"]].sum(axis=1), 1.0)
    assert out["risk_score"].between(0, 100).all()
    assert sorted(out["rank"]) == list(range(1, 95))
    assert out["risk_score"].is_monotonic_decreasing
    assert (out["target_week"] - out["week_start"] == pd.Timedelta(weeks=1)).all()
    assert out["week_start"].nunique() == 1 and out["week_start"].iloc[0] == panel["week_start"].max()
    assert set(out["classe_prevista"]) <= {0, 1, 2}
    assert (out["rotulo_previsto"] == out["classe_prevista"].map(dict(enumerate(config.CLASSES)))).all()


def test_falha_clara_quando_falta_feature(ambiente):
    _, modelo, meta, panel, clima = ambiente
    df = build_features(panel, clima, keep_last=True, city=True).drop(columns=["casos_mm4"])
    with pytest.raises(FeatureMismatch, match="casos_mm4"):
        select_features(df, meta["features"])


def test_colunas_na_ordem_do_meta(ambiente):
    _, _, meta, panel, clima = ambiente
    df = build_features(panel, clima, keep_last=True, city=True)
    embaralhado = df[list(reversed(df.columns))]
    assert list(select_features(embaralhado, meta["features"]).columns) == meta["features"]


def test_run_grava_csv_e_avisa_versao_diferente(ambiente, tmp_path, monkeypatch):
    base, _, meta, panel, clima = ambiente
    import src.predict_batch as pb

    monkeypatch.setattr(pb, "load_inputs", lambda: (panel, clima))
    meta_antigo = dict(meta, sklearn_version="0.0.1")
    (tmp_path / "meta.json").write_text(json.dumps(meta_antigo), encoding="utf-8")
    saida = tmp_path / "pred.csv"
    with pytest.warns(RuntimeWarning, match="difere da versão do treino"):
        out = run(saida, base / "m.joblib", tmp_path / "meta.json", use_registry=False)
    assert saida.exists() and len(pd.read_csv(saida)) == len(out) == 94
