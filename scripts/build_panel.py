"""Gera data/processed/panel.csv (bairro, week_start, casos) e reports/painel_qualidade.md.

Uso: python scripts/build_panel.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402
from src import data_recife as dr  # noqa: E402
from src.panel import build_panel  # noqa: E402


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    res = build_panel(dr.load_standardized())
    panel, ex = res.panel, res.extras

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    panel.assign(week_start=panel["week_start"].dt.strftime("%Y-%m-%d")).to_csv(
        config.DATA_PROCESSED / "panel.csv", index=False)

    total = int(panel["casos"].sum())
    ultimo = res.funnel[-1][1]
    por_bairro = panel.groupby("bairro")["casos"].sum().sort_values(ascending=False)
    por_ano = panel.groupby(panel["week_start"].dt.year)["casos"].sum().rename_axis("ano (início da semana)").reset_index()
    por_semana = panel.groupby("week_start")["casos"].sum().sort_values(ascending=False).head(10)

    out = ["# Qualidade do painel bairro x semana", "",
           f"Painel: **{panel['bairro'].nunique()} bairros** x **{panel['week_start'].nunique()} semanas** "
           f"({ex['first_week'].date()} a {ex['last_week'].date()}, semanas começando no domingo) = {len(panel)} linhas. "
           f"Soma de casos do painel: **{total}** (último passo do funil: {ultimo}; "
           f"{'confere' if total == ultimo else 'NÃO CONFERE'}).", "",
           "## Funil de registros", ""]
    linhas, anterior = [], None
    for etapa, n in res.funnel:
        linhas.append((etapa, n, "" if anterior is None else n - anterior))
        anterior = n
    out += [md_table(pd.DataFrame(linhas, columns=["etapa", "registros", "variação"])), ""]

    out += ["## Detalhes do funil", "",
            "**Data de referência** — casos que usaram a data de notificação no lugar da de sintomas:", ""]
    out += [f"- {k}: {v}" for k, v in ex["fallback_notificacao"].items()] or ["- nenhum"]
    out += ["", f"- Descartados sem nenhuma data válida: **{ex['descartados_sem_data']}**", "",
            "**Bairros** — registros por método de resolução (antes de descartar):", ""]
    out += [f"- {k}: {v}" for k, v in ex["bairro_metodos"].items()]
    out += ["", "Registros descartados por motivo:", ""]
    out += [f"- {k}: {v}" for k, v in ex["bairros_descartados_motivo"].items()] or ["- nenhum"]
    desc = ex["bairros_descartados_nomes"].rename("registros").reset_index().rename(
        columns={"bairro_metodo": "motivo", "nome": "valor no arquivo"})
    out += ["", "Valores descartados (todos):", "", md_table(desc), ""]
    corr = ex["bairros_corrigidos"].rename("registros").reset_index().rename(
        columns={"bairro_metodo": "método", "bairro_raw": "valor no arquivo", "bairro": "bairro oficial"})
    out += ["Valores corrigidos por apelido ou correspondência aproximada:", "", md_table(corr), ""]
    out += ["**Duplicatas**", "",
            f"- Linhas 100% idênticas removidas: {ex['duplicatas_exatas']}",
            f"- `nu_notificacao` repetido com bairro, datas e classificação iguais (removidos): {ex['duplicatas_nu_iguais']}",
            f"- Linhas com `nu_notificacao` repetido mas dados diferentes (mantidas): {ex['nu_repetido_mantido']}",
            f"- Casos fora da janela do painel (antes de {ex['first_week'].date()} ou após {ex['last_week'].date()}): "
            f"{ex['fora_da_janela']}", ""]

    out += ["## Casos totais por ano", "", md_table(por_ano), ""]
    pouco = por_bairro[por_bairro < 50].rename("casos").reset_index()
    out += [f"## Bairros com menos de 50 casos no período ({len(pouco)}; só listados, não removidos)", "",
            md_table(pouco) if len(pouco) else "Nenhum.", ""]
    out += ["## 10 bairros com mais casos", "", md_table(por_bairro.head(10).rename("casos").reset_index()), ""]
    out += ["## 10 semanas com mais casos (soma da cidade)", "",
            md_table(por_semana.rename("casos").reset_index().assign(
                week_start=lambda x: x["week_start"].dt.strftime("%Y-%m-%d"))), ""]
    sem_caso = ex["bairros_oficiais_sem_casos"]
    out += [f"## Bairros da tabela oficial sem nenhum caso no painel ({len(sem_caso)})", "",
            ", ".join(sem_caso) or "Nenhum.", ""]

    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "painel_qualidade.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Painel: {panel.shape} -> {config.DATA_PROCESSED / 'panel.csv'}")
    for etapa, n in res.funnel:
        print(f"{n:>8}  {etapa}")


if __name__ == "__main__":
    main()
