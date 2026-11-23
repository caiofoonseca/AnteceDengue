import pandas as pd

from src import data_recife as dr

CABECALHO = ["dt_notificacao", "no_bairro_residencia", "tp_classificacao_final"]
LINHAS = [
    ["2020-01-05", "SÃO JOSÉ", "10"],
    ["2020-01-06", "BOA VIAGEM", "5"],
]


def escrever(path, sep, encoding):
    texto = "\n".join(sep.join(l) for l in [CABECALHO, *LINHAS]) + "\n"
    path.write_bytes(texto.encode(encoding))


def test_le_separador_ponto_e_virgula_utf8(tmp_path):
    p = tmp_path / "dengue_2020.csv"
    escrever(p, ";", "utf-8")
    df = dr.read_csv_tolerant(p)
    assert list(df.columns) == CABECALHO
    assert df.attrs["sep"] == ";"
    assert df.loc[0, "no_bairro_residencia"] == "SÃO JOSÉ"


def test_le_latin1_com_acentos(tmp_path):
    p = tmp_path / "dengue_2019.csv"
    escrever(p, ";", "latin-1")
    df = dr.read_csv_tolerant(p)
    assert df.attrs["encoding"] == "latin-1"
    assert df.loc[0, "no_bairro_residencia"] == "SÃO JOSÉ"


def test_le_separador_virgula(tmp_path):
    p = tmp_path / "dengue_2015.csv"
    escrever(p, ",", "utf-8")
    df = dr.read_csv_tolerant(p)
    assert df.attrs["sep"] == ","
    assert df.shape == (2, 3)


def test_load_all_junta_anos_e_adiciona_ano_arquivo(tmp_path):
    escrever(tmp_path / "dengue_2019.csv", ";", "latin-1")
    escrever(tmp_path / "dengue_2020.csv", ",", "utf-8")
    df = dr.load_all(tmp_path)
    assert len(df) == 4
    assert sorted(df["ano_arquivo"].unique()) == [2019, 2020]


def test_load_all_sem_arquivos_da_erro(tmp_path):
    try:
        dr.load_all(tmp_path)
    except FileNotFoundError:
        return
    raise AssertionError("esperava FileNotFoundError")


def test_parse_date_series_aceita_formatos_mistos():
    s = pd.Series(["2013/01/04 00:00:00", "2016-01-21", "04/03/2025", "lixo", None])
    d = dr.parse_date_series(s)
    assert d.iloc[0] == pd.Timestamp("2013-01-04")
    assert d.iloc[1] == pd.Timestamp("2016-01-21")
    assert d.iloc[2] == pd.Timestamp("2025-03-04")
    assert d.iloc[3:].isna().all()
