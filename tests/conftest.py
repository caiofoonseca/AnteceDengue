import numpy as np
import pandas as pd
import pytest


def make_panel(n_weeks=60, bairros=("A", "B"), start="2020-01-05", seed=0):
    semanas = pd.date_range(start, periods=n_weeks, freq="7D")
    rng = np.random.default_rng(seed)
    linhas = []
    for i, b in enumerate(bairros):
        casos = rng.poisson(2 + 3 * i, size=n_weeks)
        linhas.append(pd.DataFrame({"bairro": b, "week_start": semanas, "casos": casos}))
    return pd.concat(linhas, ignore_index=True)


def make_clima(n_weeks=60, start="2020-01-05"):
    semanas = pd.date_range(start, periods=n_weeks, freq="7D")
    t = np.arange(n_weeks)
    return pd.DataFrame({
        "week_start": semanas,
        "temp_media": 26 + np.sin(t / 5),
        "temp_min": 24.0,
        "temp_max": 29.0,
        "umid_media": 75 + np.cos(t / 7) * 5,
        "chuva_mm": (t % 5) * 3.0,
    })


@pytest.fixture
def panel():
    return make_panel()


@pytest.fixture
def clima():
    return make_clima()
