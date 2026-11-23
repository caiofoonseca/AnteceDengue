"""Leitor tolerante dos CSVs de dengue do Portal de Dados Abertos do Recife.

Os arquivos anuais mudam de encoding (utf-8 / latin-1), de separador (; / ,) e
até de nomes de colunas entre anos. Este módulo só lê e junta os arquivos;
a harmonização dos nomes de colunas é feita em etapa posterior.
"""
import re
from pathlib import Path

import pandas as pd

from src import config

ENCODINGS = ("utf-8-sig", "latin-1")  # latin-1 aceita qualquer byte, por isso vem por último
SEPARATORS = (";", ",")


def detect_encoding(path: Path) -> str:
    """Retorna 'utf-8-sig' se o arquivo decodifica como UTF-8; senão 'latin-1'."""
    raw = Path(path).read_bytes()
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def detect_separator(path: Path, encoding: str) -> str:
    """Escolhe o separador com mais ocorrências no cabeçalho (fora de aspas)."""
    with open(path, encoding=encoding, newline="") as f:
        header = f.readline()
    header = re.sub(r'"[^"]*"', "", header)
    return max(SEPARATORS, key=header.count)


def read_csv_tolerant(path: Path) -> pd.DataFrame:
    """Lê um CSV detectando encoding e separador. Tudo vem como texto (dtype=str)."""
    path = Path(path)
    encoding = detect_encoding(path)
    sep = detect_separator(path, encoding)
    df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df.attrs["encoding"] = encoding
    df.attrs["sep"] = sep
    return df


def year_from_filename(path: Path) -> int:
    m = re.search(r"(20\d{2})", Path(path).stem)
    if not m:
        raise ValueError(f"Não achei o ano no nome do arquivo: {path.name}")
    return int(m.group(1))


def list_raw_csvs(raw_dir: Path | None = None) -> list[Path]:
    """CSVs anuais em data/raw/ (não entra em subpastas), ordenados por ano."""
    raw_dir = Path(raw_dir) if raw_dir else config.DATA_RAW
    return sorted(raw_dir.glob("*.csv"), key=year_from_filename)


def load_each(raw_dir: Path | None = None) -> dict[int, pd.DataFrame]:
    """Um DataFrame por ano, com os nomes de colunas originais do arquivo."""
    return {year_from_filename(p): read_csv_tolerant(p) for p in list_raw_csvs(raw_dir)}


def load_all(raw_dir: Path | None = None) -> pd.DataFrame:
    """Todos os CSVs em um único DataFrame, com a coluna 'ano_arquivo'.

    Nomes de colunas são convertidos para minúsculas. Colunas com nomes diferentes
    entre anos (ex.: dt_notificacao x dt_notific) continuam separadas.
    """
    frames = []
    for year, df in load_each(raw_dir).items():
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        df["ano_arquivo"] = year
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {raw_dir or config.DATA_RAW}")
    return pd.concat(frames, ignore_index=True)


# Esquema único: nome padronizado -> candidatos de coluna (minúsculas) nos arquivos de cada ano
COLUMN_MAP = {
    "nu_notificacao": ["nu_notificacao", "nu_notific"],
    "dt_notificacao": ["dt_notificacao", "dt_notific"],
    "dt_sintomas": ["dt_diagnostico_sintoma", "dt_sin_pri"],
    "bairro_raw": ["no_bairro_residencia", "nm_bairro"],
    "classi_fin": ["tp_classificacao_final", "classi_fin"],
}


def standardize(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Mapeia as colunas de um ano para o esquema único e normaliza tipos.

    - datas de formatos mistos viram datetime;
    - classificação final vira inteiro ('10.0' -> 10);
    - 'dup_exata' marca linhas 100% idênticas a outra linha do mesmo arquivo (já vistas antes).
    """
    lower = {c.lower(): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    for novo, candidatos in COLUMN_MAP.items():
        col = next((lower[c] for c in candidatos if c in lower), None)
        if col is None:
            raise KeyError(f"Ano {year}: nenhuma coluna entre {candidatos} para '{novo}'")
        out[novo] = df[col]
    out["nu_notificacao"] = out["nu_notificacao"].astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    out["dt_notificacao"] = parse_date_series(out["dt_notificacao"])
    out["dt_sintomas"] = parse_date_series(out["dt_sintomas"])
    out["classi_fin"] = pd.to_numeric(out["classi_fin"], errors="coerce").astype("Int64")
    out["ano_arquivo"] = year
    out["dup_exata"] = df.duplicated(keep="first").to_numpy()
    return out.reset_index(drop=True)


def load_standardized(raw_dir: Path | None = None) -> pd.DataFrame:
    """Todos os anos no esquema único (uma linha por notificação)."""
    frames = [standardize(df, y) for y, df in load_each(raw_dir).items()]
    if not frames:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {raw_dir or config.DATA_RAW}")
    return pd.concat(frames, ignore_index=True)


def parse_date_series(s: pd.Series) -> pd.Series:
    """Converte datas em texto para datetime, aceitando AAAA-MM-DD, AAAA/MM/DD e DD/MM/AAAA.

    Os arquivos misturam formatos (até na mesma coluna). Valores que não casam viram NaT.
    """
    s = s.astype("string").str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    ymd = s.str.match(r"^\d{4}[-/]\d{2}[-/]\d{2}", na=False)
    dmy = s.str.match(r"^\d{2}/\d{2}/\d{4}", na=False)
    out[ymd] = pd.to_datetime(s[ymd].str[:10].str.replace("/", "-"), format="%Y-%m-%d", errors="coerce")
    out[dmy] = pd.to_datetime(s[dmy].str[:10], format="%d/%m/%Y", errors="coerce")
    return out
