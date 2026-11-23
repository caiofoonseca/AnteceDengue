"""Clima semanal de Recife (um valor para o município todo).

Fontes:
- InfoDengue (alertcity, geocode 2611606): temperatura (mín/méd/máx) e umidade semanais.
  A resposta da API NÃO traz precipitação.
- Open-Meteo Historical Weather API (reanálise ERA5): precipitação diária. É a fonte de chuva usada.
  Limitação: reanálise em grade (~25 km), NÃO é observação de estação.
- INMET (estação automática A301, Recife): tentada primeiro, mas sem dados utilizáveis de chuva de 2022 em diante
  (arquivos de 2022 e 2023 vazios, 2024 e 2025 sem a estação no zip). Só serve para VALIDAR a reanálise em 2015–2021.

A semana começa no domingo (coluna week_start, mesma convenção do painel). O agrupamento é feito
pela DATA local (nunca pelo número da semana epidemiológica), então a virada de ano não é problema:
a semana de 29/12/2024 a 04/01/2025 é uma só.
"""
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src import config
from src.panel import week_start

CLIMA_RAW = config.DATA_RAW / "clima"
CLIMA_SEMANAL = config.DATA_PROCESSED / "clima_semanal.csv"

GEOCODE = 2611606
INFODENGUE_URL = "https://info.dengue.mat.br/api/alertcity"

OPENMETEO_URL = "https://archive-api.open-meteo.com/v1/archive"
RECIFE_LAT, RECIFE_LON = -8.05, -34.9  # centro aproximado do município
OPENMETEO_MODEL = "era5"
TZ_LOCAL = "America/Recife"

INMET_ZIP_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
INMET_STATION = "A301"  # RECIFE (automática)
UA = {"User-Agent": "Mozilla/5.0"}  # o portal do INMET derruba conexões sem User-Agent
MIN_HORAS_CHUVA = 0.8 * 168  # semana com menos de 80% das horas medidas não tem soma confiável

COLUNAS_SAIDA = ["week_start", "temp_media", "temp_min", "temp_max", "umid_media", "chuva_mm"]


# ---------------------------------------------------------------- download
def download_infodengue(start_year: int = config.PANEL_START_YEAR, end_year: int = config.PANEL_END_YEAR) -> Path:
    params = {"geocode": GEOCODE, "disease": "dengue", "format": "csv",
              "ew_start": 1, "ew_end": 53, "ey_start": start_year, "ey_end": end_year}
    resp = requests.get(INFODENGUE_URL, params=params, timeout=120)
    resp.raise_for_status()
    CLIMA_RAW.mkdir(parents=True, exist_ok=True)
    destino = CLIMA_RAW / f"infodengue_alertcity_{GEOCODE}.csv"
    destino.write_bytes(resp.content)
    return destino


def download_openmeteo(start_year: int = config.PANEL_START_YEAR, end_year: int = config.PANEL_END_YEAR) -> Path:
    params = {"latitude": RECIFE_LAT, "longitude": RECIFE_LON, "start_date": f"{start_year}-01-01",
              "end_date": f"{end_year}-12-31", "daily": "precipitation_sum", "models": OPENMETEO_MODEL,
              "timezone": TZ_LOCAL, "format": "csv"}
    resp = requests.get(OPENMETEO_URL, params=params, timeout=120)
    resp.raise_for_status()
    CLIMA_RAW.mkdir(parents=True, exist_ok=True)
    destino = CLIMA_RAW / "openmeteo_era5_daily_recife.csv"
    destino.write_bytes(resp.content)
    return destino


def download_inmet_year(year: int, force: bool = False) -> Path | None:
    """(Só para validação) Baixa o zip anual do INMET e guarda o CSV da estação A301 (~100 MB por zip).

    Devolve None se o zip daquele ano não tiver a estação."""
    CLIMA_RAW.mkdir(parents=True, exist_ok=True)
    destino = CLIMA_RAW / f"inmet_{INMET_STATION}_{year}.csv"
    if destino.exists() and not force:
        return destino
    resp = requests.get(INMET_ZIP_URL.format(year=year), headers=UA, timeout=600)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        membros = [n for n in zf.namelist() if f"_{INMET_STATION}_" in n.upper()]
        if not membros:
            print(f"INMET {year}: estação {INMET_STATION} não consta no zip")
            return None
        destino.write_bytes(zf.read(membros[0]))
    return destino


# ---------------------------------------------------------------- leitura
def read_infodengue(path: Path | None = None) -> pd.DataFrame:
    """Temperatura e umidade semanais do InfoDengue, com week_start = data_iniSE (domingo)."""
    df = pd.read_csv(path or CLIMA_RAW / f"infodengue_alertcity_{GEOCODE}.csv", parse_dates=["data_iniSE"])
    out = pd.DataFrame({
        "week_start": df["data_iniSE"].dt.normalize(),
        "temp_media": df["tempmed"], "temp_min": df["tempmin"], "temp_max": df["tempmax"],
        "umid_media": df["umidmed"],
    })
    assert out["week_start"].dt.weekday.eq(6).all(), "data_iniSE deveria ser sempre domingo"
    return out.drop_duplicates("week_start").sort_values("week_start").reset_index(drop=True)


def read_openmeteo_daily(path: Path | None = None) -> pd.DataFrame:
    """Chuva diária (mm) do Open-Meteo: colunas date, chuva_mm. O CSV traz 3 linhas de metadados no topo."""
    path = path or CLIMA_RAW / "openmeteo_era5_daily_recife.csv"
    linhas = Path(path).read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(linhas) if l.startswith("time,"))
    df = pd.read_csv(io.StringIO("\n".join(linhas[i:])))
    return pd.DataFrame({"date": pd.to_datetime(df.iloc[:, 0]), "chuva_mm": pd.to_numeric(df.iloc[:, 1])})


def read_inmet_hourly(path: Path) -> pd.DataFrame:
    """Lê um CSV horário do INMET e devolve (datetime_local, chuva_mm). -9999 e vazios viram NaN.

    Formato do INMET: 8 linhas de metadados, depois cabeçalho com ';', decimal com vírgula, latin-1;
    a data vem como AAAA-MM-DD ou AAAA/MM/DD, a hora como '0000' ou '0000 UTC' (sempre UTC).
    """
    raw = Path(path).read_bytes()
    try:
        texto = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = raw.decode("latin-1")
    linhas = texto.splitlines()
    i = next(k for k, l in enumerate(linhas) if l.lower().startswith("data") and "hora" in l.lower())
    df = pd.read_csv(io.StringIO("\n".join(linhas[i:])), sep=";", decimal=",", dtype=str, index_col=False)
    c_data = next(c for c in df.columns if c.lower().startswith("data"))
    c_hora = next(c for c in df.columns if c.lower().startswith("hora"))
    c_chuva = next(c for c in df.columns if "precipita" in c.lower())
    data = pd.to_datetime(df[c_data].str.strip().str.replace("/", "-"), format="%Y-%m-%d", errors="coerce")
    hora = pd.to_numeric(df[c_hora].str.extract(r"(\d{2})")[0], errors="coerce")
    utc = (data + pd.to_timedelta(hora, unit="h")).dt.tz_localize("UTC")
    chuva = pd.to_numeric(df[c_chuva].str.replace(",", ".").str.strip(), errors="coerce")
    chuva = chuva.where(chuva > -999)  # -9999 = sem dado
    out = pd.DataFrame({"datetime_local": utc.dt.tz_convert(TZ_LOCAL).dt.tz_localize(None), "chuva_mm": chuva})
    return out[out["datetime_local"].notna()].reset_index(drop=True)


# ---------------------------------------------------------------- agregação
def weekly_rain_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Soma semanal (domingo a sábado) da chuva diária. Colunas: week_start, chuva_mm, dias_chuva.

    chuva_mm fica NaN se a semana não tem os 7 dias (ex.: semana cortada no início/fim da série).
    """
    d = daily.copy()
    d["week_start"] = week_start(d["date"])
    g = d.groupby("week_start").agg(chuva_mm=("chuva_mm", "sum"), dias_chuva=("chuva_mm", "count"))
    g.loc[g["dias_chuva"] < 7, "chuva_mm"] = float("nan")
    return g.reset_index()


def weekly_rain(hourly: pd.DataFrame) -> pd.DataFrame:
    """(Validação) Soma semanal da chuva horária local. NaN se < 80% das 168 horas foram medidas."""
    h = hourly.copy()
    h["week_start"] = week_start(h["datetime_local"])
    g = h.groupby("week_start").agg(chuva_mm=("chuva_mm", "sum"), horas_chuva=("chuva_mm", "count"))
    g.loc[g["horas_chuva"] < MIN_HORAS_CHUVA, "chuva_mm"] = float("nan")
    return g.reset_index()


def build_weekly_climate(infodengue: pd.DataFrame, rain_weekly: pd.DataFrame) -> pd.DataFrame:
    """Junta temperatura/umidade (InfoDengue) com a chuva semanal. Mantém as semanas do InfoDengue."""
    return infodengue.merge(rain_weekly[["week_start", "chuva_mm"]], on="week_start", how="left")


def build_all(download: bool = True) -> pd.DataFrame:
    """Baixa (opcional), monta e grava data/processed/clima_semanal.csv."""
    if download:
        download_infodengue()
        download_openmeteo()
    weekly = build_weekly_climate(read_infodengue(), weekly_rain_daily(read_openmeteo_daily()))
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    weekly[COLUNAS_SAIDA].assign(week_start=weekly["week_start"].dt.strftime("%Y-%m-%d")).to_csv(
        CLIMA_SEMANAL, index=False)
    return weekly
