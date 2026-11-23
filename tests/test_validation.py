import numpy as np
import pandas as pd

from src import config
from src.features import build_features
from src.labels import fit_thresholds
from src.validation import expanding_window_splits, temporal_split
from tests.conftest import make_clima, make_panel

UMA = pd.Timedelta(weeks=1)


def _df(n_weeks=120):
    return build_features(make_panel(n_weeks=n_weeks), make_clima(n_weeks))


def test_tamanhos_e_ordem_dos_conjuntos():
    df = _df()
    s = temporal_split(df, val_weeks=10, test_weeks=10, gap_weeks=1)
    assert s.val["week_start"].nunique() == 10
    assert s.test["week_start"].nunique() == 10
    assert s.train["week_start"].max() < s.val["week_start"].min() < s.val["week_start"].max() < s.test["week_start"].min()
    assert s.test["week_start"].max() == df["week_start"].max()


def test_alvo_da_ultima_linha_do_treino_nao_cai_na_validacao():
    s = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1)
    alvo_treino = s.train["week_start"].max() + UMA
    assert alvo_treino < s.val["week_start"].min()
    alvo_val = s.val["week_start"].max() + UMA
    assert alvo_val < s.test["week_start"].min()


def test_gap_exclui_semanas_entre_conjuntos():
    s = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1)
    assert s.val["week_start"].min() - s.train["week_start"].max() == 2 * UMA
    assert s.test["week_start"].min() - s.val["week_start"].max() == 2 * UMA


def test_conjuntos_sem_sobreposicao_de_linhas():
    s = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1)
    chaves = [set(zip(d["bairro"], d["week_start"])) for d in (s.train, s.val, s.test)]
    assert not chaves[0] & chaves[1] and not chaves[1] & chaves[2] and not chaves[0] & chaves[2]


def test_limiares_do_split_vem_so_do_treino():
    s = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1)
    assert s.thresholds == fit_thresholds(s.train["target_casos"])
    assert s.thresholds[0] < s.thresholds[1]


def test_splits_expansivos_nunca_usam_dado_futuro():
    treino = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1).train
    folds = expanding_window_splits(treino, n_splits=4, gap_weeks=1)
    assert len(folds) == 4
    tamanhos = [len(f.train_idx) for f in folds]
    assert tamanhos == sorted(tamanhos) and len(set(tamanhos)) == len(tamanhos)
    for f in folds:
        tr, va = treino.iloc[f.train_idx], treino.iloc[f.valid_idx]
        assert len(np.intersect1d(f.train_idx, f.valid_idx)) == 0
        assert tr["week_start"].max() + UMA < va["week_start"].min()
        assert va["week_start"].min() - tr["week_start"].max() == 2 * UMA


def test_limiares_de_cada_fold_usam_so_o_treino_do_fold():
    treino = temporal_split(_df(), val_weeks=10, test_weeks=10, gap_weeks=1).train.copy()
    treino.loc[treino["week_start"] >= treino["week_start"].unique()[-15], "target_casos"] = 500.0
    folds = expanding_window_splits(treino, n_splits=3, gap_weeks=1)
    primeiro = folds[0]
    assert primeiro.thresholds == fit_thresholds(treino.iloc[primeiro.train_idx]["target_casos"])
    assert primeiro.thresholds[1] < 100
    assert len(primeiro.y_train) == len(primeiro.train_idx)
    assert len(primeiro.y_valid) == len(primeiro.valid_idx)


def test_folds_usam_parametros_do_config_por_padrao():
    treino = temporal_split(_df(200), val_weeks=10, test_weeks=10).train
    assert len(expanding_window_splits(treino)) == config.CV_SPLITS
