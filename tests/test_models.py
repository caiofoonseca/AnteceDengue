import numpy as np
import pytest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from src import config
from src.models import CLASS_WEIGHT_SUPPORT, NEEDS_SCALER, build_model, candidate_names


def test_candidatos_pedidos():
    assert set(candidate_names()) == {"logreg", "knn", "tree", "rf", "adaboost", "mlp"}


@pytest.mark.parametrize("name", ["logreg", "knn", "tree", "rf", "adaboost", "mlp"])
def test_pipeline_com_imputer_mediana_e_scaler_quando_precisa(name):
    pipe = build_model(name)
    etapas = dict(pipe.named_steps)
    assert isinstance(etapas["imputer"], SimpleImputer) and etapas["imputer"].strategy == "median"
    assert ("scaler" in etapas) == (name in NEEDS_SCALER)
    if "scaler" in etapas:
        assert isinstance(etapas["scaler"], StandardScaler)
    assert list(pipe.named_steps)[0] == "imputer"


@pytest.mark.parametrize("name", ["logreg", "knn", "tree", "rf", "adaboost", "mlp"])
def test_random_state_e_class_weight(name):
    clf = build_model(name).named_steps["clf"]
    params = clf.get_params()
    if "random_state" in params:
        assert params["random_state"] == config.SEED
    suporte = CLASS_WEIGHT_SUPPORT[name]
    if suporte == "balanced":
        assert params["class_weight"] == "balanced"
    if name == "adaboost":
        assert params["estimator"].class_weight == "balanced"
    if name in ("knn", "mlp"):
        assert "class_weight" not in params


@pytest.mark.parametrize("name", ["logreg", "knn", "tree", "rf", "adaboost", "mlp"])
def test_treina_e_preve_com_nulos(name):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(120, 5))
    X[::7, 2] = np.nan
    y = (X[:, 0] > 0).astype(int) + (X[:, 1] > 1).astype(int)
    pipe = build_model(name).fit(X, y)
    proba = pipe.predict_proba(X)
    assert proba.shape[0] == 120
    assert np.allclose(proba.sum(axis=1), 1.0)


def test_imputer_ajustado_so_no_treino():
    pipe = build_model("logreg")
    X_tr = np.array([[1.0], [2.0], [3.0], [np.nan]] * 10)
    y = np.array([0, 1] * 20)
    pipe.fit(X_tr, y)
    assert pipe.named_steps["imputer"].statistics_[0] == 2.0
    X_novo = np.array([[100.0], [np.nan]])
    pipe.predict(X_novo)
    assert pipe.named_steps["imputer"].statistics_[0] == 2.0
