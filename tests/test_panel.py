import pandas as pd

from src import data_recife as dr
from src.panel import add_reference_date, build_panel, complete_panel, last_complete_week, week_start

OFICIAIS = ["BOA VIAGEM", "GRACAS", "IBURA"]
T = pd.Timestamp


def test_week_start_e_domingo():
    datas = pd.Series(pd.to_datetime(["2025-01-05", "2025-01-04", "2025-12-31", "2025-01-06"]))
    ws = week_start(datas)
    assert ws.dt.weekday.eq(6).all()
    assert list(ws) == [T("2025-01-05"), T("2024-12-29"), T("2025-12-28"), T("2025-01-05")]


def test_ultima_semana_completa():
    assert last_complete_week(T("2025-12-31")) == T("2025-12-21")
    assert last_complete_week(T("2025-12-27")) == T("2025-12-21")


def test_data_de_sintomas_absurda_cai_para_notificacao():
    df = pd.DataFrame({
        "ano_arquivo": [2025, 2025, 2025, 2025, 2025],
        "dt_notificacao": pd.to_datetime(["2025-03-10"] * 4 + [None]),
        "dt_sintomas": pd.to_datetime(["1950-01-11",
                                       "2025-03-12",
                                       None,
                                       "2025-03-08",
                                       None]),
    })
    r = add_reference_date(df)
    assert list(r["dt_ref"][:4]) == [T("2025-03-10")] * 3 + [T("2025-03-08")]
    assert list(r["ref_fonte"][:4]) == ["notificacao", "notificacao", "notificacao", "sintomas"]
    assert pd.isna(r["dt_ref"].iloc[4])


def test_ano_anterior_ao_arquivo_ainda_e_valido():
    df = pd.DataFrame({"ano_arquivo": [2016], "dt_notificacao": [T("2016-01-05")],
                       "dt_sintomas": [T("2015-12-30")]})
    assert add_reference_date(df)["dt_ref"].iloc[0] == T("2015-12-30")


def test_painel_completo_com_zeros():
    counts = pd.DataFrame({"bairro": ["IBURA"], "week_start": [T("2025-01-12")], "casos": [3]})
    p = complete_panel(counts, ["IBURA", "GRACAS"], T("2025-01-05"), T("2025-01-19"))
    assert len(p) == 2 * 3
    assert not p.duplicated(["bairro", "week_start"]).any()
    assert p["casos"].sum() == 3
    assert p.loc[(p.bairro == "GRACAS"), "casos"].eq(0).all()


def _fake():
    linhas = [
        ("1", "2020-03-10", "2020-03-08", "Ibura", 10, 2020, False),
        ("2", "2020-03-11", "2020-03-09", "IBURA", 11, 2020, False),
        ("3", "2020-03-11", "2020-03-09", "IBURA", 5, 2020, False),
        ("4", "2020-03-11", "2020-03-09", "GRAAS", 12, 2020, False),
        ("5", "2020-03-12", "2020-03-10", "ZONA RURAL", 10, 2020, False),
        ("6", "2020-03-12", None, None, 10, 2020, False),
        ("7", "2020-03-20", "1950-01-01", "BOA VIAGEM", 3, 2020, False),
        ("8", "2020-03-20", "2020-03-18", "BOA VIAGEM", 1, 2020, False),
        ("8", "2020-03-20", "2020-03-18", "BOA VIAGEM", 1, 2020, False),
        ("9", "2020-03-20", "2020-03-18", "IBURA", 10, 2020, False),
        ("9", "2020-03-21", "2020-03-19", "BOA VIAGEM", 10, 2020, False),
        ("10", "2020-03-22", "2020-03-20", "IBURA", 10, 2020, True),
        ("11", "2014-03-10", "2014-03-08", "IBURA", 10, 2014, False),
        ("12", "2020-03-28", "2020-03-23", "IBURA", 10, 2020, False),
    ]
    df = pd.DataFrame(linhas, columns=["nu_notificacao", "dt_notificacao", "dt_sintomas", "bairro_raw",
                                       "classi_fin", "ano_arquivo", "dup_exata"])
    df["dt_notificacao"] = pd.to_datetime(df["dt_notificacao"])
    df["dt_sintomas"] = pd.to_datetime(df["dt_sintomas"])
    df["classi_fin"] = df["classi_fin"].astype("Int64")
    return df


def test_soma_do_painel_igual_aos_casos_validos():
    res = build_panel(_fake(), official=OFICIAIS)
    etapas = dict(res.funnel)
    assert etapas["Registros lidos (2013–2025)"] == 14
    assert etapas["Após período 2015–2025"] == 13
    assert etapas["Após caso confirmado"] == 12
    assert etapas["Após data válida"] == 12
    assert etapas["Após bairro válido"] == 10
    assert etapas["Após duplicatas"] == 8
    assert etapas["Após janela do painel (casos no painel)"] == 8
    casos = res.funnel[-1][1]
    assert res.panel["casos"].sum() == casos
    assert not res.panel.duplicated(["bairro", "week_start"]).any()
    assert list(res.panel.columns) == ["bairro", "week_start", "casos"]
    assert res.extras["nu_repetido_mantido"] == 2
    assert res.extras["bairros_descartados_motivo"] == {"não é bairro": 1, "nulo": 1}


def test_standardize_mapeia_esquemas_antigo_e_novo():
    antigo = pd.DataFrame({"nu_notificacao": ["1.0"], "dt_notificacao": ["2016-01-21"],
                           "dt_diagnostico_sintoma": ["2016-01-07"], "no_bairro_residencia": ["IBURA"],
                           "tp_classificacao_final": ["10.0"]})
    novo = pd.DataFrame({"NU_NOTIFIC": ["2"], "DT_NOTIFIC": ["04/03/2025"], "DT_SIN_PRI": ["02/03/2025"],
                         "NM_BAIRRO": ["PINA"], "CLASSI_FIN": ["5"]})
    a, n = dr.standardize(antigo, 2016), dr.standardize(novo, 2025)
    assert list(a.columns) == list(n.columns)
    assert a["classi_fin"].iloc[0] == 10 and n["classi_fin"].iloc[0] == 5
    assert a["nu_notificacao"].iloc[0] == "1"
    assert n["dt_sintomas"].iloc[0] == T("2025-03-02")
