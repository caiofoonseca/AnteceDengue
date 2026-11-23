"""Validação temporal: holdout cronológico e CV de janela expansiva (sem embaralhar, sem k-fold).

Cada linha t usa features até a semana t e tem alvo na semana t+1. Para não vazar o futuro:
  - o alvo da última linha de um conjunto (semana a+1) cai ANTES da primeira linha do conjunto
    seguinte;
  - GAP_WEEKS semanas de linhas (a+1 ... a+GAP) são excluídas entre um conjunto e o seguinte, então
    o conjunto seguinte começa na semana a + 1 + GAP.
Os limiares de rótulo são ajustados só nos alvos do conjunto de treino de cada split.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import config
from src.labels import apply_thresholds, fit_thresholds

SEMANA = pd.Timedelta(weeks=1)


@dataclass
class Split:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    gap_weeks: int
    thresholds: tuple[float, float]


@dataclass
class Fold:
    train_idx: np.ndarray
    valid_idx: np.ndarray
    thresholds: tuple[float, float]
    y_train: np.ndarray
    y_valid: np.ndarray


def _weeks(df: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(df["week_start"].unique())


def temporal_split(df: pd.DataFrame, val_weeks: int = config.VAL_WEEKS, test_weeks: int = config.TEST_WEEKS,
                   gap_weeks: int = config.GAP_WEEKS) -> Split:
    """Treino | gap | validação (val_weeks) | gap | teste (test_weeks).

    df: saída de build_features (todas as linhas com alvo). O teste são as últimas test_weeks semanas.
    """
    semanas = _weeks(df)
    n = len(semanas)
    if n <= val_weeks + test_weeks + 2 * gap_weeks + 1:
        raise ValueError("poucas semanas para o split pedido")
    t0 = n - test_weeks
    v_fim = t0 - 1 - gap_weeks
    v0 = v_fim - val_weeks + 1
    a = v0 - 1 - gap_weeks
    ws = df["week_start"]
    train = df[ws <= semanas[a]]
    val = df[(ws >= semanas[v0]) & (ws <= semanas[v_fim])]
    test = df[ws >= semanas[t0]]
    thr = fit_thresholds(train["target_casos"])
    return Split(train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True),
                 gap_weeks, thr)


def expanding_window_splits(train_df: pd.DataFrame, n_splits: int = config.CV_SPLITS,
                            gap_weeks: int = config.GAP_WEEKS) -> list[Fold]:
    """CV de janela expansiva sobre o treino: o treino de cada fold cresce e a validação é o bloco seguinte.

    Blocos de validação do mesmo tamanho cobrem o fim do treino; tudo antes do primeiro bloco
    (menos o gap) é o treino do fold 1. Os limiares de rótulo de cada fold usam só os alvos do
    treino daquele fold.
    """
    df = train_df.reset_index(drop=True)
    semanas = _weeks(df)
    n = len(semanas)
    b = n // (n_splits + 1)
    if b < 1:
        raise ValueError("semanas insuficientes para o número de splits")
    base = n - n_splits * b
    ws = df["week_start"].to_numpy()
    folds = []
    for k in range(n_splits):
        vs = base + k * b
        a = vs - 1 - gap_weeks
        tr = np.flatnonzero(ws <= semanas[a])
        va = np.flatnonzero((ws >= semanas[vs]) & (ws <= semanas[vs + b - 1]))
        thr = fit_thresholds(df.loc[tr, "target_casos"])
        folds.append(Fold(tr, va, thr, apply_thresholds(df.loc[tr, "target_casos"], thr),
                          apply_thresholds(df.loc[va, "target_casos"], thr)))
    return folds
