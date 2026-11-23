"""Análise da cauda da série: fração de registros ainda sem classificação final definitiva.

Os casos mais recentes demoram a ser classificados (nulo ou 8 = inconclusivo), então as últimas
semanas ficam artificialmente baixas se contarmos só os confirmados.
"""
import pandas as pd

from src import config
from src.panel import add_reference_date, week_start

TAIL_MARGIN = 0.05


def pending_by_week(df: pd.DataFrame) -> pd.DataFrame:
    """Por semana de sintomas (data de referência): registros, % pendentes e confirmados.

    Considera todas as classificações (antes do filtro de caso confirmado). Pendente =
    classificação nula ou 8 (inconclusivo).
    """
    d = df[df["ano_arquivo"].between(config.PANEL_START_YEAR, config.PANEL_END_YEAR)]
    d = add_reference_date(d)
    d = d[d["dt_ref"].notna()].copy()
    d["week_start"] = week_start(d["dt_ref"])
    d["pendente"] = d["classi_fin"].isna() | (d["classi_fin"] == 8)
    d["confirmado"] = d["classi_fin"].isin(config.CASE_CODES)
    g = d.groupby("week_start").agg(registros=("pendente", "size"), frac_pendente=("pendente", "mean"),
                                    confirmados=("confirmado", "sum"))
    return g.reset_index()


def choose_panel_end(weekly: pd.DataFrame, ref_start: str, ref_end: str,
                     margin: float = TAIL_MARGIN) -> tuple[pd.Timestamp, float, float]:
    """Última semana confiável.

    Referência = fração média de pendentes entre ref_start e ref_end (meses 'estáveis').
    Limite = referência + margin. PANEL_END = última semana depois da qual a fração passa
    do limite e não volta mais a ficar abaixo dele.
    Retorna (panel_end, referencia, limite).
    """
    w = weekly.sort_values("week_start").reset_index(drop=True)
    ref = w[(w["week_start"] >= ref_start) & (w["week_start"] <= ref_end)]["frac_pendente"].mean()
    limite = ref + margin
    acima = w["frac_pendente"] > limite
    depois = w["week_start"] > pd.Timestamp(ref_end)
    abaixo_depois = w[~acima & depois]
    ultima_ok = abaixo_depois["week_start"].max() if len(abaixo_depois) else pd.Timestamp(ref_end)
    return ultima_ok, float(ref), float(limite)
