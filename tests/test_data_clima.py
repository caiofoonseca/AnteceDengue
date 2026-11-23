import pandas as pd

from src import data_clima as dc

T = pd.Timestamp

INMET_FALSO = """REGIAO:;NE
UF:;PE
ESTACAO:;RECIFE
CODIGO (WMO):;A301
LATITUDE:;-8,05
LONGITUDE:;-34,95
ALTITUDE:;10
DATA DE FUNDACAO:;2004-12-21
DATA (YYYY-MM-DD);HORA (UTC);PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA DO AR (°C);
2024-12-31;0200;1,5;25,0;
2024-12-31;0300;-9999;25,0;
2025-01-01;1200;2,0;27,0;
"""


def horario(inicio, horas, chuva):
    """Série horária local com a mesma chuva em todas as horas."""
    idx = pd.date_range(inicio, periods=horas, freq="h")
    return pd.DataFrame({"datetime_local": idx, "chuva_mm": chuva})


def test_le_inmet_com_metadados_virgula_e_menos_9999(tmp_path):
    p = tmp_path / "inmet.csv"
    p.write_bytes(INMET_FALSO.encode("latin-1"))
    h = dc.read_inmet_hourly(p)
    assert len(h) == 3
    assert h["chuva_mm"].iloc[0] == 1.5
    assert pd.isna(h["chuva_mm"].iloc[1])
    assert h["datetime_local"].iloc[0] == T("2024-12-30 23:00")


def test_semana_comeca_no_domingo_e_soma_chuva():
    h = horario("2025-01-05 00:00", 7 * 24, 0.5)
    w = dc.weekly_rain(h)
    assert list(w["week_start"]) == [T("2025-01-05")]
    assert w["chuva_mm"].iloc[0] == 84.0
    assert w["week_start"].dt.weekday.eq(6).all()


def test_virada_de_ano_fica_na_mesma_semana():
    h = horario("2024-12-29 00:00", 7 * 24, 1.0)
    w = dc.weekly_rain(h)
    assert len(w) == 1
    assert w["week_start"].iloc[0] == T("2024-12-29")
    assert w["chuva_mm"].iloc[0] == 168.0


def test_semana_com_pouca_cobertura_vira_nula():
    h = horario("2025-01-05 00:00", 7 * 24, 1.0)
    h.loc[:60, "chuva_mm"] = float("nan")
    w = dc.weekly_rain(h)
    assert pd.isna(w["chuva_mm"].iloc[0])
    assert w["horas_chuva"].iloc[0] == 107


def diario(inicio, dias, chuva):
    return pd.DataFrame({"date": pd.date_range(inicio, periods=dias, freq="D"), "chuva_mm": chuva})


def test_chuva_diaria_soma_semanal_e_virada_de_ano():
    w = dc.weekly_rain_daily(diario("2024-12-29", 7, 2.0))
    assert list(w["week_start"]) == [T("2024-12-29")]
    assert w["chuva_mm"].iloc[0] == 14.0


def test_chuva_diaria_semana_incompleta_vira_nula():
    w = dc.weekly_rain_daily(diario("2025-01-01", 10, 1.0))
    assert list(w["week_start"]) == [T("2024-12-29"), T("2025-01-05")]
    assert pd.isna(w["chuva_mm"].iloc[0])
    assert pd.isna(w["chuva_mm"].iloc[1])


def test_le_openmeteo_com_metadados(tmp_path):
    p = tmp_path / "om.csv"
    p.write_text("latitude,longitude,elevation\n-8.0,-35.0,11.0\n\ntime,precipitation_sum (mm)\n"
                 "2025-01-01,3.70\n2025-01-02,0.00\n", encoding="utf-8")
    d = dc.read_openmeteo_daily(p)
    assert list(d["chuva_mm"]) == [3.7, 0.0]
    assert d["date"].iloc[0] == T("2025-01-01")


def test_junta_clima_semanal_com_chuva():
    info = pd.DataFrame({"week_start": [T("2025-01-05"), T("2025-01-12")], "temp_media": [26.0, 27.0],
                         "temp_min": [24.0, 25.0], "temp_max": [29.0, 30.0], "umid_media": [75.0, 80.0]})
    out = dc.build_weekly_climate(info, dc.weekly_rain_daily(diario("2025-01-05", 7, 12.0)))
    assert list(out["week_start"]) == [T("2025-01-05"), T("2025-01-12")]
    assert out["chuva_mm"].iloc[0] == 84.0
    assert pd.isna(out["chuva_mm"].iloc[1])
