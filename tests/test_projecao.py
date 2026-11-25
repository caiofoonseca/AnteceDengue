import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.repository import Repository
from src import projecao as pj
from src.labels import fit_thresholds

BAIRROS = ("BOA VIAGEM", "VARZEA", "COHAB")


def synthetic_panel(first="2015-01-04", last="2025-08-17", seed=0):
    """Painel semanal sazonal (pico em julho) e com ano epidêmico em 2024, só para testar o código."""
    rng = np.random.default_rng(seed)
    semanas = pd.date_range(first, last, freq="7D")
    linhas = []
    for i, bairro in enumerate(BAIRROS):
        for semana in semanas:
            sazonal = 1 + np.cos(2 * np.pi * (semana.dayofyear - 190) / 365)
            fator = 3.0 if semana.year == 2024 else 1.0
            linhas.append((bairro, semana, int(rng.poisson((i + 1) * 2 * sazonal * fator))))
    return pd.DataFrame(linhas, columns=["bairro", "week_start", "casos"])


@pytest.fixture(scope="module")
def panel():
    return synthetic_panel()


@pytest.fixture(scope="module")
def monthly(panel):
    return pj.monthly_panel(panel)


def test_semana_que_cruza_meses_conta_para_o_mes_do_domingo():
    semanas = pd.date_range("2025-03-02", "2025-05-04", freq="7D")
    panel = pd.DataFrame({"bairro": "A", "week_start": semanas, "casos": 1})
    panel.loc[panel["week_start"] == "2025-03-30", "casos"] = 100
    mensal = pj.monthly_panel(panel).set_index("mes")
    assert mensal.loc[3, "casos_brutos"] == 4 + 100 and mensal.loc[3, "n_semanas"] == 5
    assert mensal.loc[4, "casos_brutos"] == 4
    assert set(mensal.index) == {3, 4}


def test_casos_sao_padronizados_por_domingos_do_mes():
    semanas = pd.date_range("2025-03-02", "2025-04-27", freq="7D")
    panel = pd.DataFrame({"bairro": "A", "week_start": semanas, "casos": 3})
    mensal = pj.monthly_panel(panel).set_index("mes")
    assert mensal.loc[3, "casos"] == pytest.approx(3 * 52 / 12) and mensal.loc[4, "casos"] == pytest.approx(3 * 52 / 12)


def test_meses_incompletos_do_painel_sao_descartados(monthly):
    ultimo = monthly[monthly["ano"] == 2025]["mes"].max()
    primeiro = monthly[monthly["ano"] == 2015]["mes"].min()
    assert ultimo == 7 and primeiro == 1
    assert monthly.groupby("bairro").size().nunique() == 1


def test_limiares_so_do_treino(monthly):
    historico = monthly[monthly["ano"] <= 2023]
    assert pj.fit_month_thresholds(historico) == fit_thresholds(historico["casos"])
    alterado = monthly.copy()
    alterado.loc[alterado["ano"] >= 2024, "casos"] *= 50
    a = pj.backtest(monthly, 2023, 2024, methods=("climatologia",))["climatologia"]["limiares"]
    b = pj.backtest(alterado, 2023, 2024, methods=("climatologia",))["climatologia"]["limiares"]
    assert a == b == list(fit_thresholds(historico["casos"]))


@pytest.mark.parametrize("metodo", pj.METHODS)
def test_metodos_recusam_historico_com_o_periodo_projetado(monthly, metodo):
    with pytest.raises(ValueError, match="vazamento"):
        pj.forecast(metodo, monthly[monthly["ano"] <= 2024], 2024)


@pytest.mark.parametrize("metodo", pj.METHODS)
def test_projecao_nao_depende_do_periodo_projetado(monthly, metodo):
    historico = monthly[monthly["ano"] <= 2023]
    futuro_alterado = monthly.copy()
    futuro_alterado.loc[futuro_alterado["ano"] >= 2024, "casos"] = 9999.0
    a = pj.forecast(metodo, historico, 2024)
    b = pj.forecast(metodo, futuro_alterado[futuro_alterado["ano"] <= 2023], 2024)
    pd.testing.assert_series_equal(a, b)


def test_metodos_simples_com_valores_conhecidos():
    historico = pd.DataFrame({"bairro": "A", "ano": [2022, 2023], "mes": 1, "casos": [10.0, 20.0]})
    assert pj.forecast_climatology(historico, 2024).iloc[0] == 15.0
    assert pj.forecast_last_year(historico, 2024).iloc[0] == 20.0
    assert pj.forecast_recency(historico, 2024, 1).iloc[0] == pytest.approx((10 * 0.25 + 20 * 0.5) / 0.75)


def test_ultimo_ano_usa_o_ano_mais_recente_que_tem_o_mes():
    historico = pd.DataFrame({"bairro": "A", "ano": [2023, 2024, 2024], "mes": [8, 1, 8], "casos": [5.0, 7.0, 9.0]})
    historico = historico[~((historico["ano"] == 2024) & (historico["mes"] == 8))]
    previsto = pj.forecast_last_year(historico, 2025)
    assert previsto.loc[("A", 8)] == 5.0 and previsto.loc[("A", 1)] == 7.0


def test_avaliacao_perfeita_e_pior_caso():
    real = pd.DataFrame({"bairro": ["A", "B", "C"] * 2, "mes": [1] * 3 + [2] * 3,
                         "casos": [0.0, 3.0, 10.0, 1.0, 5.0, 20.0]})
    perfeito = real.set_index(["bairro", "mes"])["casos"]
    m = pj.evaluate(real, perfeito, (0.5, 4.0))
    assert m["f1_macro"] == 1.0 and m["recall_alto"] == 1.0 and m["mae_casos_mes"] == 0.0
    assert m["pico_acerto"] == 1.0 and m["spearman_bairros"] == pytest.approx(1.0)
    invertido = perfeito.iloc[::-1].set_axis(perfeito.index)
    assert pj.evaluate(real, invertido, (0.5, 4.0))["spearman_bairros"] < 0


def test_escolha_pelo_backtest_a_ignora_o_baseline():
    a = {"ultimo_ano": {"f1_macro": 0.99, "mae_casos_mes": 1.0}, "climatologia": {"f1_macro": 0.4, "mae_casos_mes": 3.0},
         "recencia_h1": {"f1_macro": 0.5, "mae_casos_mes": 5.0}, "recencia_h2": {"f1_macro": 0.5, "mae_casos_mes": 2.0}}
    assert pj.choose_method(a) == "recencia_h2"


def test_projecao_final_formato_do_csv(monthly):
    projecao, limiares = pj.project_year(monthly, 2026, "recencia_h1", "2025-08-17")
    assert list(projecao.columns) == pj.CSV_COLUMNS
    assert len(projecao) == len(BAIRROS) * 12 and projecao.isna().sum().sum() == 0
    assert sorted(projecao["mes"].unique()) == [f"2026-{m:02d}" for m in range(1, 13)]
    assert set(projecao["classe_risco"]) <= {0, 1, 2} and set(projecao["confianca"]) <= {"alta", "media", "baixa"}
    assert (projecao["p25"] <= projecao["p75"]).all() and (projecao["casos_esperados"] >= 0).all()
    assert (projecao["metodo"] == "recencia_h1").all() and (projecao["ultima_data_real_usada"] == "2025-08-17").all()
    assert limiares[0] < limiares[1]


def test_confianca_baixa_com_poucos_anos():
    historico = pd.DataFrame({"bairro": "A", "ano": [2023, 2024], "mes": 1, "casos": [5.0, 5.0]})
    wide = historico.pivot_table(index=["bairro", "mes"], columns="ano", values="casos")
    previsto = pd.Series([5.0], index=wide.index)
    assert pj.confidence(wide, previsto, (1.0, 4.0)).iloc[0] == "baixa"


def test_aviso_fixo():
    assert pj.warning_text("2025-08-17") == ("Projeção sazonal baseada no histórico até 17/08/2025; "
                                            "não há dados reais de 2026 para verificação.")


@pytest.fixture(scope="module")
def arquivos(panel, tmp_path_factory):
    base = tmp_path_factory.mktemp("proj")
    saida, meta = base / "projecao.csv", base / "meta.json"
    resultado = pj.run_all(panel, mlflow_enabled=False, output=saida, meta_path=meta, backtest_path=base / "bt.json", report_path=None)
    return saida, meta, resultado


def test_run_all_grava_csv_meta_e_escolhe_pelo_backtest_a(arquivos):
    saida, meta, resultado = arquivos
    texto = json.loads(meta.read_text(encoding="utf-8"))
    assert texto["metodo"] == pj.choose_method(texto["backtest_a"]["metodos"]) == resultado["metodo"]
    assert texto["backtest_b"]["treino_ate"] == 2024 and texto["backtest_b"]["projeta"] == 2025
    assert texto["ultimo_mes_completo"] == "2025-07" and len(texto["curva_cidade"]) == 12
    df = pd.read_csv(saida)
    assert len(df) == 36 and df.isna().sum().sum() == 0
    assert not list(saida.parent.glob("*.tmp"))


def test_run_all_e_deterministico(panel, arquivos, tmp_path):
    saida, _, _ = arquivos
    pj.run_all(panel, mlflow_enabled=False, output=tmp_path / "x.csv", meta_path=tmp_path / "m.json",
               backtest_path=tmp_path / "b.json", report_path=None)
    assert (tmp_path / "x.csv").read_bytes() == saida.read_bytes()


@pytest.fixture
def client(arquivos, tmp_path):
    saida, meta, _ = arquivos
    painel = tmp_path / "panel.csv"
    synthetic_panel("2025-01-05", "2025-02-02").to_csv(painel, index=False)
    repo = Repository(panel_path=painel, predictions_path=tmp_path / "x.csv", database_url="sqlite://",
                      projection_path=saida, projection_meta_path=meta)
    modelo = SimpleNamespace(meta={"model_name": "teste"}, source="teste")
    with TestClient(create_app(modelo, repo)) as c:
        yield c


def test_endpoint_devolve_aviso_e_itens(client):
    r = client.get("/projecao/2026")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["aviso"] == "Projeção sazonal baseada no histórico até 17/08/2025; não há dados reais de 2026 para verificação."
    assert corpo["total"] == 36 and len(corpo["curva_cidade"]) == 12 and "escolhido" in corpo["backtest_b"]
    assert {"bairro", "mes", "casos_esperados", "classe_risco", "p25", "p75", "confianca"} <= set(corpo["items"][0])


def test_endpoint_filtros_bairro_e_mes(client):
    assert client.get("/projecao/2026", params={"bairro": "boa viagem"}).json()["total"] == 12
    for mes in ("7", "07", "2026-07"):
        corpo = client.get("/projecao/2026", params={"mes": mes}).json()
        assert corpo["total"] == 3 and {i["mes"] for i in corpo["items"]} == {"2026-07"}
    assert client.get("/projecao/2026", params={"bairro": "BOA VIAGEM", "mes": "3"}).json()["total"] == 1
    assert client.get("/projecao/2026", params={"mes": "13"}).status_code == 404
    assert client.get("/projecao/2026", params={"bairro": "NAO EXISTE"}).status_code == 404


def test_endpoint_sem_arquivos_responde_503(tmp_path):
    repo = Repository(panel_path=tmp_path / "p.csv", predictions_path=tmp_path / "x.csv", database_url="sqlite://",
                      projection_path=tmp_path / "nao.csv", projection_meta_path=tmp_path / "nao.json")
    modelo = SimpleNamespace(meta={"model_name": "teste"}, source="teste")
    with TestClient(create_app(modelo, repo)) as c:
        r = c.get("/projecao/2026")
    assert r.status_code == 503 and "python -m src.projecao" in r.json()["detail"]


def test_docs_do_endpoint_descrevem_formula(client):
    descricao = client.get("/openapi.json").json()["paths"]["/projecao/2026"]["get"]["description"]
    assert "`casos_brutos / domingos_do_mês * 52/12`" in descricao and "não é previsão verificada" in descricao
