import pandas as pd
import pytest

from src.evaluate import class_distribution, compute_metrics, persistence_baseline


def test_metricas_de_predicao_perfeita():
    y = [0, 1, 2, 2, 1, 0]
    m = compute_metrics(y, y)
    assert m["f1_macro"] == 1.0
    assert m["balanced_accuracy"] == 1.0
    assert m["recall_alto"] == 1.0
    assert m["confusion_matrix"] == [[2, 0, 0], [0, 2, 0], [0, 0, 2]]


def test_recall_por_classe_e_matriz():
    m = compute_metrics([0, 0, 1, 2, 2, 2], [0, 1, 1, 2, 0, 2])
    assert m["recall_baixo"] == 0.5
    assert m["recall_medio"] == 1.0
    assert m["recall_alto"] == pytest.approx(2 / 3)
    assert m["confusion_matrix"][2] == [1, 0, 2]


def test_baseline_de_persistencia_repete_a_classe_de_t():
    df = pd.DataFrame({"casos_t": [0, 0, 1, 5, 5], "target_casos": [0, 3, 1, 0, 5]})
    thr = (0.0, 2.0)
    m = persistence_baseline(df, thr)
    assert m["confusion_matrix"] == [[1, 0, 1], [0, 1, 0], [1, 0, 1]]


def test_distribuicao_de_classes():
    d = class_distribution([0, 0, 0, 1, 2])
    assert d["baixo"] == (3, 60.0)
    assert d["medio"] == (1, 20.0)
    assert d["alto"] == (1, 20.0)
