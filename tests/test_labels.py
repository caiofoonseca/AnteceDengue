import numpy as np
import pytest

from src.labels import apply_thresholds, fit_thresholds


def test_limiares_estritamente_crescentes_em_dados_normais():
    q_mid, q_high = fit_thresholds([0, 0, 0, 1, 2, 3, 5, 8, 13, 21])
    assert q_mid < q_high


def test_limiares_crescentes_mesmo_com_quase_so_zeros():
    q_mid, q_high = fit_thresholds([0] * 95 + [1, 1, 2, 3, 7])
    assert q_mid == 0.0
    assert q_mid < q_high


def test_limiares_crescentes_quando_tudo_e_zero():
    q_mid, q_high = fit_thresholds([0, 0, 0, 0])
    assert (q_mid, q_high) == (0.0, 1.0)


def test_regra_baixo_zero_medio_ate_q_high_alto_acima():
    thr = (0.0, 2.0)
    assert list(apply_thresholds([0, 1, 2, 3, 10], thr)) == [0, 1, 1, 2, 2]


def test_apply_rejeita_limiares_nao_crescentes():
    with pytest.raises(ValueError):
        apply_thresholds([1, 2], (2.0, 2.0))


def test_fit_usa_so_o_que_recebe():
    assert fit_thresholds(np.zeros(50))[0] == 0.0
    assert fit_thresholds(np.arange(100))[0] == pytest.approx(59.4)
