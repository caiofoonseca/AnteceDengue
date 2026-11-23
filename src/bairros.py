"""Normalização e resolução dos nomes de bairro contra a Tabela de Bairros do portal."""
import difflib
import re
import unicodedata
from pathlib import Path

import pandas as pd

from src import config
from src.bairro_aliases import ALIASES, NOT_BAIRRO
from src.data_recife import read_csv_tolerant

TABELA_BAIRROS = config.DATA_RAW / "auxiliares" / "tabela_de_bairros.csv"

EXATO, ALIAS, APROXIMADO = "exato", "apelido", "aproximado"
NULO, NAO_BAIRRO, NAO_ENCONTRADO = "nulo", "não é bairro", "não encontrado na tabela"


def normalize_name(s) -> str | None:
    """Maiúsculas, sem acento, sem pontuação e sem espaços extras. Nulo vira None."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or s is pd.NA:
        return None
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[.\-/_]", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def load_official(path: Path | None = None) -> list[str]:
    """Nomes oficiais de bairro (normalizados), sem 'BAIRRO IGNORADO'."""
    tb = read_csv_tolerant(path or TABELA_BAIRROS)
    nomes = {normalize_name(n) for n in tb["Nome Localidade"]}
    return sorted(n for n in nomes if n and n not in NOT_BAIRRO)


def resolve_bairro(raw, official: list[str], cutoff: float | None = None) -> tuple[str | None, str]:
    """Resolve um nome bruto para um bairro oficial.

    Ordem: igualdade exata -> dicionário de apelidos -> correspondência aproximada
    (limiar alto e sem ambiguidade). Retorna (nome_oficial | None, método_ou_motivo).
    """
    cutoff = config.BAIRRO_FUZZY_CUTOFF if cutoff is None else cutoff
    nome = normalize_name(raw)
    if nome is None:
        return None, NULO
    if nome in NOT_BAIRRO:
        return None, NAO_BAIRRO
    oficiais = set(official)
    if nome in oficiais:
        return nome, EXATO
    alvo = ALIASES.get(nome)
    if alvo is not None and alvo in oficiais:
        return alvo, ALIAS
    cands = difflib.get_close_matches(nome, official, n=2, cutoff=cutoff)
    if cands:
        if len(cands) == 1:
            return cands[0], APROXIMADO
        r1 = difflib.SequenceMatcher(None, nome, cands[0]).ratio()
        r2 = difflib.SequenceMatcher(None, nome, cands[1]).ratio()
        if r1 - r2 >= 0.03:
            return cands[0], APROXIMADO
    return None, NAO_ENCONTRADO
