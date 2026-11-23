"""Analisa a cauda de 2025 e gera reports/cauda_2025.md e reports/cauda_2025.png.

Uso: python scripts/analyze_tail.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src import data_recife as dr
from src.tail import TAIL_MARGIN, choose_panel_end, pending_by_week

REF_START, REF_END = "2025-01-05", "2025-06-29"
N_SEMANAS = 32

AZUL, CINZA, LARANJA = "#2b6cb0", "#6b7280", "#c2410c"


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    weekly = pending_by_week(dr.load_standardized())
    end, ref, limite = choose_panel_end(weekly, REF_START, REF_END)
    cauda = weekly.tail(N_SEMANAS).reset_index(drop=True)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
    x = cauda["week_start"]
    a1.plot(x, cauda["frac_pendente"] * 100, color=AZUL, lw=2, marker="o", ms=4)
    a1.axhline(ref * 100, color=CINZA, lw=1, ls="--")
    a1.axhline(limite * 100, color=LARANJA, lw=1, ls="--")
    a1.text(x.iloc[-14], limite * 100 + 1.2, f"limite = referência + {TAIL_MARGIN * 100:.0f} p.p. ({limite * 100:.1f}%)",
            color=LARANJA, fontsize=8)
    a1.text(x.iloc[-14], ref * 100 + 1.2, f"referência jan–jun/2025 ({ref * 100:.1f}%)", color=CINZA, fontsize=8)
    a1.set_ylabel("% nulos ou inconclusivos")
    a1.set_title("Registros sem classificação definitiva, por semana de sintomas", fontsize=10, loc="left")
    a2.bar(x, cauda["confirmados"], width=5, color=AZUL)
    a2.set_ylabel("casos confirmados")
    a2.set_title("Casos confirmados por semana (o que o painel enxerga)", fontsize=10, loc="left")
    for a in (a1, a2):
        a.axvline(end + pd.Timedelta(days=3.5), color=LARANJA, lw=1.2)
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#e5e7eb", lw=0.6)
    a2.text(end + pd.Timedelta(days=5), a2.get_ylim()[1] * 0.85, f"PANEL_END = {end.date()}\n(cortar daqui para frente)",
            color=LARANJA, fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    config.REPORTS_DIR.mkdir(exist_ok=True)
    fig.savefig(config.REPORTS_DIR / "cauda_2025.png", dpi=130)

    t = cauda.assign(
        week_start=cauda["week_start"].dt.strftime("%Y-%m-%d"),
        frac_pendente=(cauda["frac_pendente"] * 100).round(1).astype(str) + "%",
        dentro=cauda["week_start"].map(lambda s: "sim" if s <= end else "não"),
    ).rename(columns={"week_start": "semana (domingo)", "frac_pendente": "% pendentes", "dentro": "no painel"})
    out = ["# Cauda de 2025: casos ainda sem classificação", "",
           "Pendente = classificação final nula ou 8 (inconclusivo), contada sobre **todos** os registros da semana "
           "de sintomas (antes do filtro de caso confirmado).", "",
           "## Critério", "",
           f"- Referência: fração média de pendentes em {REF_START} a {REF_END} (26 semanas): **{ref * 100:.2f}%**.",
           f"- Limite: referência + {TAIL_MARGIN * 100:.0f} pontos percentuais = **{limite * 100:.2f}%**.",
           f"- **PANEL_END = {end.date()}**: última semana com fração dentro do limite; da semana seguinte em diante "
           "a fração fica acima do limite e não volta.", "",
           "![cauda](cauda_2025.png)", "",
           f"## Últimas {N_SEMANAS} semanas", "", md_table(t), ""]
    (config.REPORTS_DIR / "cauda_2025.md").write_text("\n".join(out), encoding="utf-8")
    print(f"referência={ref:.4f} limite={limite:.4f} PANEL_END proposto={end.date()} (config: {config.PANEL_END})")


if __name__ == "__main__":
    main()
