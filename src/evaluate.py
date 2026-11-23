"""Métricas de classificação e baseline de persistência."""
import numpy as np
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, recall_score

from src import config
from src.labels import apply_thresholds

LABELS = [0, 1, 2]


def compute_metrics(y_true, y_pred) -> dict:
    """F1-macro, balanced accuracy, recall por classe e matriz de confusão (linhas = real)."""
    rec = recall_score(y_true, y_pred, labels=LABELS, average=None, zero_division=0)
    return {
        "f1_macro": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        **{f"recall_{nome}": float(r) for nome, r in zip(config.CLASSES, rec)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
    }


def persistence_baseline(df, thresholds: tuple[float, float]) -> dict:
    """Baseline ingênuo: prevê para t+1 a classe dos casos de t, com os MESMOS limiares do treino.

    df precisa das colunas casos_t e target_casos. Retorna as métricas contra a classe real de t+1.
    """
    y_pred = apply_thresholds(df["casos_t"], thresholds)
    y_true = apply_thresholds(df["target_casos"], thresholds)
    return compute_metrics(y_true, y_pred)


def class_distribution(y) -> dict:
    """Contagem e % por classe."""
    y = np.asarray(y)
    n = len(y)
    return {nome: (int((y == i).sum()), (float((y == i).mean() * 100) if n else 0.0))
            for i, nome in enumerate(config.CLASSES)}
