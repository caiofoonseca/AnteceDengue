import numpy as np
import pandas as pd
import pytest

from src import config
from src.features import build_features, feature_columns
from src.tracking import Tracker
from src.train import TestSetLocked, locked_split, run_experiment
from tests.conftest import make_clima, make_panel


@pytest.fixture
def df():
    return build_features(make_panel(n_weeks=170, bairros=("A", "B", "C")), make_clima(170))


def test_guarda_bloqueia_o_teste(df):
    split = locked_split(df)
    assert len(split.train) > 0 and len(split.val) > 0
    assert split.thresholds[0] < split.thresholds[1]
    with pytest.raises(TestSetLocked, match="conjunto de teste"):
        split.test


def test_treino_falha_se_pedir_o_teste(df, monkeypatch, tmp_path):
    import src.train as train

    original = train.evaluate_candidate

    def malicioso(name, split, folds, figures_dir):
        split.test
        return original(name, split, folds, figures_dir)

    monkeypatch.setattr(train, "evaluate_candidate", malicioso)
    with pytest.raises(TestSetLocked):
        run_experiment(["logreg"], "x", df, Tracker("x", enabled=False), tmp_path, tmp_path / "fig", "m.csv", False)


def test_experimento_completo_sem_tocar_no_teste(df, tmp_path):
    tabela = run_experiment(["logreg", "tree"], "x", df, Tracker("x", enabled=False), tmp_path, tmp_path / "fig",
                            "metricas.csv", True)
    assert list(tabela["modelo"]) == ["Persistência", "LogisticRegression", "DecisionTree"]
    lido = pd.read_csv(tmp_path / "metricas.csv")
    assert len(lido) == 3
    for col in ("f1_macro_cv_f2_5", "f1_macro_val", "recall_alto_val", "gap_treino_val"):
        assert col in lido.columns
    assert (tmp_path / "fig" / "cm_logreg.png").exists()
    assert (tmp_path / "fig" / "roc_tree.png").exists()
    assert (tmp_path / "fig" / "gap_overfitting.png").exists()


def test_persistencia_usa_o_mesmo_split_que_os_modelos(df, tmp_path):
    tabela = run_experiment(["logreg"], "x", df, Tracker("x", enabled=False), tmp_path, tmp_path / "fig",
                            "m.csv", False)
    split = locked_split(df)
    from src.evaluate import persistence_baseline

    esperado = persistence_baseline(split.val, split.thresholds)["f1_macro"]
    assert tabela.loc[0, "f1_macro_val"] == pytest.approx(esperado)


def test_importancia_do_rf_e_gravada(df, tmp_path):
    run_experiment(["rf"], "x", df, Tracker("x", enabled=False), tmp_path, tmp_path / "fig", "m.csv", True)
    imp = pd.read_csv(tmp_path / "importancia_rf.csv")
    assert len(imp) == len(feature_columns())
    assert np.isclose(imp["importancia"].sum(), 1.0)


def test_tracker_desligado_nao_faz_nada():
    t = Tracker("exp", enabled=False)
    with t.run("r") as run:
        run.log_params({"a": 1})
        run.log_metrics({"m": 1.0})
        run.log_dict({"x": 1}, "x.json")
    assert t._mlflow is None


def test_tracker_registra_no_mlflow_com_versao_do_sklearn(tmp_path, monkeypatch):
    import mlflow
    import sklearn

    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    t = Tracker("exp-teste", enabled=True)
    with t.run("run1", {"tipo": "modelo"}) as run:
        run.log_params({"p": 3})
        run.log_metrics({"f1": 0.5})
    runs = mlflow.search_runs(experiment_names=["exp-teste"])
    assert len(runs) == 1
    assert runs.loc[0, "params.sklearn_version"] == sklearn.__version__
    assert runs.loc[0, "metrics.f1"] == 0.5
