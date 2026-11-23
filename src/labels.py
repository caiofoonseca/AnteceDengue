"""Rótulos de risco (0 = baixo, 1 = médio, 2 = alto) a partir de casos(t+1) e limiares do treino."""
import numpy as np
import pandas as pd

from src import config


def fit_thresholds(casos_treino) -> tuple[float, float]:
    """Limiares (q_mid, q_high) = quantis Q_MID e Q_HIGH dos casos do TREINO.

    Regra de classes (ver apply_thresholds): baixo = casos <= q_mid; médio = casos <= q_high;
    alto = acima de q_high. Como há muitos zeros no painel, q_mid costuma ser 0
    (baixo = nenhum caso). Os limiares são sempre estritamente crescentes: se q_high <= q_mid,
    q_high vira o menor valor de casos do treino acima de q_mid (ou q_mid + 1 se não houver).
    """
    x = np.asarray(pd.Series(casos_treino).dropna(), dtype=float)
    if x.size == 0:
        raise ValueError("casos_treino vazio")
    q_mid, q_high = (float(np.quantile(x, q)) for q in (config.Q_MID, config.Q_HIGH))
    if q_high <= q_mid:
        acima = x[x > q_mid]
        q_high = float(acima.min()) if acima.size else q_mid + 1.0
    return q_mid, q_high


def apply_thresholds(casos, thresholds: tuple[float, float]) -> np.ndarray:
    """0 se casos <= q_mid; 1 se casos <= q_high; 2 caso contrário."""
    q_mid, q_high = thresholds
    if not q_mid < q_high:
        raise ValueError(f"limiares devem ser estritamente crescentes, recebi {thresholds}")
    c = np.asarray(casos, dtype=float)
    return np.where(c <= q_mid, 0, np.where(c <= q_high, 1, 2)).astype(int)
