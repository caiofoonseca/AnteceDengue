"""Baixa o clima, gera data/processed/clima_semanal.csv e reports/clima_qualidade.md (+ .png).

Uso: python scripts/build_clima.py [--sem-download]
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402
from src import data_clima as dc  # noqa: E402

AZUL, LARANJA = "#2b6cb0", "#c2410c"


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def validar_com_inmet(chuva_om: pd.DataFrame) -> tuple[str, int]:
    """Compara a chuva semanal do Open-Meteo (que alimenta o modelo) com o INMET A301.

    O INMET entra só como verificação de sanidade, nas semanas em que tem >= 80% das horas medidas.
    Devolve (texto em markdown com tabela por ano e total, número de semanas comparadas).
    """
    partes = [dc.read_inmet_hourly(p) for p in sorted(dc.CLIMA_RAW.glob("inmet_A301_*.csv"))]
    if not partes:
        return "Arquivos do INMET não encontrados em data/raw/clima/; verificação não executada.", 0
    inmet = dc.weekly_rain(pd.concat(partes, ignore_index=True)).dropna(subset=["chuva_mm"])
    j = inmet.merge(chuva_om[["week_start", "chuva_mm"]], on="week_start", suffixes=("_inmet", "_om")).dropna()
    j = j[j["week_start"] >= "2015-01-04"].assign(ano=lambda x: x["week_start"].dt.year)

    def resumo(g: pd.DataFrame) -> list:
        return [len(g), f"{g['chuva_mm_inmet'].corr(g['chuva_mm_om']):.2f}",
                f"{g['chuva_mm_inmet'].corr(g['chuva_mm_om'], method='spearman'):.2f}",
                f"{g['chuva_mm_om'].sum() / g['chuva_mm_inmet'].sum():.2f}"]

    linhas = []
    for ano in range(config.PANEL_START_YEAR, config.PANEL_END_YEAR + 1):
        g = j[j["ano"] == ano]
        linhas.append([ano, *resumo(g)] if len(g) >= 10 else [ano, len(g), "—", "—", "—"])
    linhas.append(["**total**", *resumo(j)])
    tab = pd.DataFrame(linhas, columns=["ano", "semanas comparadas", "Pearson", "Spearman", "chuva Open-Meteo / INMET"])
    anos_usados = sorted(j["ano"].unique())
    texto = (f"Anos do INMET usados na comparação: **{', '.join(map(str, anos_usados))}** "
             f"({len(j)} semanas, {j['week_start'].min().date()} a {j['week_start'].max().date()}). "
             "Sem dado de chuva utilizável no INMET: 2022 e 2023 (arquivos vazios), 2024 e 2025 (estação ausente no zip). "
             "Em 2021 só entram as semanas com >= 80% das horas medidas.\n\n" + md_table(tab))
    return texto, len(j)


def main() -> None:
    download = "--sem-download" not in sys.argv
    weekly = dc.build_all(download=download)
    chuva_om = dc.weekly_rain_daily(dc.read_openmeteo_daily())

    # semanas do painel (2015-01-04 até PANEL_END)
    semanas = pd.date_range("2015-01-04", pd.Timestamp(config.PANEL_END), freq="7D")
    na_painel = weekly[weekly["week_start"].isin(semanas)]
    faltam_linha = sorted(set(semanas) - set(weekly["week_start"]))
    cols = ["temp_media", "temp_min", "temp_max", "umid_media", "chuva_mm"]
    nulos = pd.DataFrame({
        "coluna": cols,
        "% nulos (série toda)": [f"{weekly[c].isna().mean() * 100:.1f}%" for c in cols],
        "% nulos (semanas do painel)": [f"{na_painel[c].isna().mean() * 100:.1f}%" for c in cols],
    })
    sem_valor = na_painel[na_painel[cols].isna().any(axis=1)][["week_start"] + cols]
    est = weekly[cols].describe().T[["mean", "std", "min", "50%", "max"]].round(1).reset_index()
    est.columns = ["coluna", "média", "desvio", "mín", "mediana", "máx"]
    valid_txt, _ = validar_com_inmet(chuva_om)

    # gráfico: temperatura e chuva (dois painéis, sem eixo duplo)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.8), sharex=True)
    a1.plot(weekly["week_start"], weekly["temp_media"], color=LARANJA, lw=1)
    a1.set_ylabel("temperatura média (°C)")
    a2.bar(weekly["week_start"], weekly["chuva_mm"], width=6, color=AZUL)
    a2.set_ylabel("chuva na semana (mm)")
    for a in (a1, a2):
        a.axvline(pd.Timestamp(config.PANEL_END), color="#6b7280", lw=1, ls="--")
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#e5e7eb", lw=0.6)
    a1.set_title("Clima semanal de Recife (linha tracejada = PANEL_END)", fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(config.REPORTS_DIR / "clima_qualidade.png", dpi=130)

    out = ["# Qualidade do clima semanal", "",
           "## Fontes", "",
           "- **Temperatura e umidade:** InfoDengue (`alertcity`, geocode 2611606), valores semanais do município. "
           "A resposta real da API não traz precipitação.",
           "- **Chuva (alimenta o modelo, fonte única em todo o período 2015 até PANEL_END):** Open-Meteo "
           "Historical Weather API, modelo ERA5. **É reanálise em grade (~25 km), não medição de estação.** "
           "Precipitação diária somada por semana (domingo a sábado, dia local de Recife).",
           "- **INMET (estação A301 de Recife):** NÃO alimenta o modelo. Usado só como verificação de sanidade "
           "nos anos em que tem dado (seção abaixo), porque não tem chuva utilizável de 2022 em diante.", "",
           "## Cobertura", "",
           f"- Período: {weekly['week_start'].min().date()} a {weekly['week_start'].max().date()} "
           f"({len(weekly)} semanas).",
           f"- Semanas do painel ({semanas[0].date()} a {semanas[-1].date()}): {len(semanas)}; "
           f"sem linha no arquivo de clima: {len(faltam_linha)}.",
           f"- Semanas do painel com algum valor de clima nulo: {len(sem_valor)}.", "",
           "## % de nulos", "", md_table(nulos), ""]
    if len(sem_valor):
        sv = sem_valor.assign(week_start=sem_valor["week_start"].dt.strftime("%Y-%m-%d"))
        out += ["Semanas do painel com nulos:", "", md_table(sv.round(1).fillna("—")), ""]
    out += ["## Estatísticas básicas (série toda)", "", md_table(est), "",
            "## Verificação de sanidade da chuva (Open-Meteo x INMET A301)", "", valid_txt, "",
            "![clima](clima_qualidade.png)", ""]
    (config.REPORTS_DIR / "clima_qualidade.md").write_text("\n".join(out), encoding="utf-8")
    print(f"clima_semanal: {len(weekly)} semanas, {weekly['week_start'].min().date()} a {weekly['week_start'].max().date()}")
    print(f"painel: {len(semanas)} semanas; sem linha: {len(faltam_linha)}; com nulo: {len(sem_valor)}")
    print(valid_txt)


if __name__ == "__main__":
    main()
