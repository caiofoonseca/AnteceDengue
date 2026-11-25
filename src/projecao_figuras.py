"""Figuras da projeção sazonal (reports/figuras/): curva da cidade, Backtest B e mapa de um mês de pico.

Uso: python -m src.projecao_figuras
Lê data/processed (projecao_2026_mensal.csv, projecao_2026_meta.json, panel.csv) e reproduz o Backtest B só para
desenhar a série real contra a projetada. Nada aqui altera o modelo semanal nem o teste final.
"""
import json
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

from src import config
from src import projecao as pj

log = logging.getLogger("projecao_figuras")
GEOJSON = config.ROOT / "app" / "assets" / "bairros.geojson"
MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
ACCENT, GRAY, INK = "#c2410c", "#b8b2a9", "#1f2937"


def fig_seasonal_curve(meta: dict, destino) -> None:
    curva = pd.DataFrame(meta["curva_cidade"])
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for ano, valores in meta["historico_cidade"].items():
        y = [np.nan if v is None else v for v in valores]
        ax.plot(MONTHS, y, color=GRAY, lw=1.1, label="Anos reais" if ano == min(meta["historico_cidade"]) else None)
        indice = max(i for i, v in enumerate(y) if v == v)
        if np.nanmax(y) > 1000 or ano == max(meta["historico_cidade"]):
            ax.annotate(ano, (indice, y[indice]), fontsize=8, color="#7a736a", xytext=(3, 0), textcoords="offset points")
    ax.fill_between(MONTHS, curva["p25"], curva["p75"], color=ACCENT, alpha=0.15, label="p25 a p75 dos anos reais")
    ax.plot(MONTHS, curva["casos_esperados"], color=ACCENT, lw=3, marker="o", label="Projeção 2026")
    ax.set_ylabel("Casos por mês (soma dos 94 bairros)")
    ax.set_title("Curva sazonal da cidade: anos reais e projeção de 2026", loc="left", color=INK)
    ax.text(0, -0.1, f"Projeção do padrão sazonal ({meta['metodo']}), não é previsão verificada."
            f"{chr(10)}{meta['aviso']}",
            transform=ax.transAxes, fontsize=8, color="#555", va="top")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def fig_backtest_b(monthly: pd.DataFrame, meta: dict, destino) -> None:
    b = meta["backtest_b"]
    history = monthly[monthly["ano"] <= b["treino_ate"]]
    real = monthly[monthly["ano"] == b["projeta"]]
    meses = sorted(real["mes"].unique())
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot([MONTHS[m - 1] for m in meses], real.groupby("mes")["casos"].sum().loc[meses], color=INK, lw=3, marker="o",
            label=f"Real {b['projeta']}")
    for metodo, cor, rotulo in ((meta["metodo"], ACCENT, f"Projetado ({meta['metodo']})"),
                                (pj.BASELINE, GRAY, "Baseline: mesmo mês do último ano")):
        previsto = pj.forecast(metodo, history, b["projeta"]).groupby(level="mes").sum().loc[meses]
        ax.plot([MONTHS[m - 1] for m in meses], previsto, color=cor, lw=2, marker="s", ls="--", label=rotulo)
    ax.set_ylabel("Casos por mês (soma dos 94 bairros)")
    ax.set_title(f"Backtest B: treino até {b['treino_ate']}, real x projetado em {b['projeta']}", loc="left", color=INK)
    ax.text(0, -0.1, f"Só meses completos até {meta['ultimo_mes_completo']}. Método escolhido pelo Backtest A.",
            transform=ax.transAxes, fontsize=8, color="#555")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)


def fig_peak_map(projecao: pd.DataFrame, meta: dict, destino) -> str:
    curva = pd.DataFrame(meta["curva_cidade"])
    pico = curva.loc[curva["casos_esperados"].idxmax(), "mes"]
    valores = projecao[projecao["mes"] == pico].set_index("bairro")["casos_esperados"]
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    patches, cores = [], []
    for feat in geo["features"]:
        poligonos = feat["geometry"]["coordinates"]
        if feat["geometry"]["type"] == "Polygon":
            poligonos = [poligonos]
        for poligono in poligonos:
            patches.append(Polygon(np.asarray(poligono[0]), closed=True))
            cores.append(valores.get(feat["properties"]["bairro"], np.nan))
    fig, ax = plt.subplots(figsize=(7, 8.2))
    colecao = PatchCollection(patches, cmap="Oranges", edgecolor="white", linewidth=0.4)
    colecao.set_array(np.asarray(cores))
    colecao.set_clim(0, float(valores.quantile(0.98)))
    ax.add_collection(colecao)
    ax.autoscale_view()
    ax.set_aspect(1 / np.cos(np.deg2rad(8.06)))
    ax.axis("off")
    barra = fig.colorbar(colecao, ax=ax, shrink=0.5)
    barra.set_label("Casos esperados por mês")
    ax.set_title(f"Projeção sazonal, mês de pico da cidade ({pico})", loc="left", color=INK)
    fig.text(0.02, 0.02, f"Projeção do padrão sazonal, não é previsão verificada."
             f"{chr(10)}{meta['aviso']}", fontsize=7, color="#555")
    fig.tight_layout()
    fig.savefig(destino, dpi=150)
    plt.close(fig)
    return pico


def main() -> None:
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    meta = json.loads(config.PROJECTION_META_PATH.read_text(encoding="utf-8"))
    projecao = pd.read_csv(config.PROJECTION_PATH)
    monthly = pj.monthly_panel(pd.read_csv(config.PANEL_PATH))
    pj.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_seasonal_curve(meta, pj.FIGURES_DIR / "projecao_curva_sazonal.png")
    fig_backtest_b(monthly, meta, pj.FIGURES_DIR / "projecao_backtest_b.png")
    pico = fig_peak_map(projecao, meta, pj.FIGURES_DIR / "projecao_mapa_mes_pico.png")
    log.info("figuras gravadas em %s (mês de pico: %s)", pj.FIGURES_DIR, pico)


if __name__ == "__main__":
    main()
