"""Painel de casos confirmados por bairro x semana epidemiológica (semana começa no domingo)."""
from dataclasses import dataclass, field

import pandas as pd

from src import config
from src.bairros import (ALIAS, APROXIMADO, EXATO, NAO_BAIRRO, NAO_ENCONTRADO, NULO,
                         load_official, resolve_bairro)


def week_start(dates: pd.Series) -> pd.Series:
    """Domingo da semana de cada data (segunda=0 ... domingo=6 em weekday())."""
    d = pd.to_datetime(dates).dt.normalize()
    return d - pd.to_timedelta((d.dt.weekday + 1) % 7, unit="D")


def add_reference_date(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta dt_ref (data de referência do caso) e ref_fonte.

    Usa a data de início dos sintomas. Cai para a data de notificação quando os sintomas
    estão nulos, absurdos (ano anterior a ano_arquivo - 1) ou posteriores à notificação.
    Sem nenhuma data válida, dt_ref fica NaT.
    """
    df = df.copy()
    sint, notif = df["dt_sintomas"], df["dt_notificacao"]
    nula = sint.isna()
    antiga = sint.dt.year < (df["ano_arquivo"] - 1)
    posterior = sint > notif
    ok = ~nula & ~antiga & ~posterior.fillna(False)
    df["dt_ref"] = sint.where(ok, notif)
    df["ref_fonte"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[ok, "ref_fonte"] = "sintomas"
    df.loc[~ok & notif.notna(), "ref_fonte"] = "notificacao"
    df["motivo_fallback"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[~ok & nula, "motivo_fallback"] = "sintomas nulos"
    df.loc[~ok & ~nula & antiga, "motivo_fallback"] = "sintomas absurdos (anteriores ao ano do arquivo - 1)"
    df.loc[~ok & ~nula & ~antiga, "motivo_fallback"] = "sintomas posteriores à notificação"
    return df


def last_complete_week(max_date: pd.Timestamp) -> pd.Timestamp:
    """Início da última semana (dom-sáb) totalmente coberta pela data máxima observada."""
    inicio = week_start(pd.Series([max_date])).iloc[0]
    return inicio if (max_date - inicio).days >= 6 else inicio - pd.Timedelta(days=7)


def complete_panel(counts: pd.DataFrame, bairros: list[str], first: pd.Timestamp,
                   last: pd.Timestamp) -> pd.DataFrame:
    """Painel completo bairro x semana (zeros onde não há casos). counts: bairro, week_start, casos."""
    semanas = pd.date_range(first, last, freq="7D")
    idx = pd.MultiIndex.from_product([sorted(bairros), semanas], names=["bairro", "week_start"])
    s = counts.set_index(["bairro", "week_start"])["casos"].reindex(idx, fill_value=0)
    return s.astype(int).reset_index()


@dataclass
class PanelResult:
    panel: pd.DataFrame
    funnel: list[tuple[str, int]]
    extras: dict = field(default_factory=dict)


def build_panel(df: pd.DataFrame, official: list[str] | None = None) -> PanelResult:
    """Constrói o painel a partir do DataFrame padronizado (data_recife.load_standardized)."""
    official = official if official is not None else load_official()
    funnel: list[tuple[str, int]] = [("Registros lidos (2013–2025)", len(df))]
    ex: dict = {}

    # 1. período
    d = df[df["ano_arquivo"].between(config.PANEL_START_YEAR, config.PANEL_END_YEAR)]
    funnel.append((f"Após período {config.PANEL_START_YEAR}–{config.PANEL_END_YEAR}", len(d)))

    # 2. caso confirmado
    d = d[d["classi_fin"].isin(config.CASE_CODES)]
    funnel.append(("Após caso confirmado", len(d)))

    # 3. data válida
    d = add_reference_date(d)
    ex["fallback_notificacao"] = d["motivo_fallback"].value_counts().to_dict()
    sem_data = d["dt_ref"].isna()
    ex["descartados_sem_data"] = int(sem_data.sum())
    d = d[~sem_data]
    funnel.append(("Após data válida", len(d)))

    # 4. bairro válido
    resolvido = {raw: resolve_bairro(raw, official) for raw in d["bairro_raw"].dropna().unique()}

    def _resolve(raw):
        return resolvido[raw] if pd.notna(raw) else (None, NULO)

    pares = d["bairro_raw"].map(_resolve)
    d = d.assign(bairro=pares.map(lambda p: p[0]), bairro_metodo=pares.map(lambda p: p[1]))
    ex["bairro_metodos"] = d["bairro_metodo"].value_counts().to_dict()
    sem_bairro = d["bairro"].isna()
    ex["bairros_descartados_motivo"] = d.loc[sem_bairro, "bairro_metodo"].value_counts().to_dict()
    ex["bairros_descartados_nomes"] = (
        d.loc[sem_bairro].assign(nome=lambda x: x["bairro_raw"].fillna("<nulo>"))
        .groupby(["bairro_metodo", "nome"]).size().sort_values(ascending=False)
    )
    ex["bairros_corrigidos"] = (
        d[d["bairro_metodo"].isin([ALIAS, APROXIMADO])]
        .groupby(["bairro_metodo", "bairro_raw", "bairro"]).size().sort_values(ascending=False)
    )
    d = d[~sem_bairro]
    funnel.append(("Após bairro válido", len(d)))

    # 5. duplicatas
    exatas = d["dup_exata"].sum()
    d = d[~d["dup_exata"]]
    chave = ["nu_notificacao", "ano_arquivo", "bairro", "dt_sintomas", "dt_notificacao", "classi_fin"]
    tem_nu = d["nu_notificacao"].notna()
    dup_nu = d.duplicated(subset=chave, keep="first") & tem_nu
    ex["duplicatas_exatas"] = int(exatas)
    ex["duplicatas_nu_iguais"] = int(dup_nu.sum())
    d = d[~dup_nu]
    mesma_nu = d["nu_notificacao"].notna() & d.duplicated(subset=["nu_notificacao", "ano_arquivo"], keep=False)
    ex["nu_repetido_mantido"] = int(mesma_nu.sum())
    funnel.append(("Após duplicatas", len(d)))

    # 6. janela do painel
    d = d.assign(week_start=week_start(d["dt_ref"]))
    first = week_start(pd.Series([pd.Timestamp(f"{config.PANEL_START_YEAR}-01-01")])).iloc[0]
    if first < pd.Timestamp(f"{config.PANEL_START_YEAR}-01-01"):
        first += pd.Timedelta(days=7)  # primeira semana inteira dentro do período
    last_dados = last_complete_week(df.loc[df["ano_arquivo"] <= config.PANEL_END_YEAR, "dt_notificacao"].max())
    last = min(last_dados, pd.Timestamp(config.PANEL_END))  # corta a cauda ainda não classificada
    ex["ultima_semana_completa_dados"] = last_dados
    na_janela = d["week_start"].between(first, last)
    ex["fora_da_janela"] = int((~na_janela).sum())
    d = d[na_janela]
    funnel.append(("Após janela do painel (casos no painel)", len(d)))

    counts = d.groupby(["bairro", "week_start"]).size().rename("casos").reset_index()
    bairros = sorted(d["bairro"].unique())
    panel = complete_panel(counts, bairros, first, last)
    ex["first_week"], ex["last_week"] = first, last
    ex["bairros_oficiais_sem_casos"] = sorted(set(official) - set(bairros))
    return PanelResult(panel=panel, funnel=funnel, extras=ex)
