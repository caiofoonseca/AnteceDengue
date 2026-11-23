"""Gera reports/split_resumo.md: split temporal, limiares, distribuição de classes e baseline de persistência.

Uso: python scripts/make_split_summary.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src.evaluate import class_distribution, persistence_baseline
from src.features import build_features, feature_columns, load_inputs
from src.labels import apply_thresholds
from src.validation import expanding_window_splits, temporal_split

UMA = pd.Timedelta(weeks=1)


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def d(x) -> str:
    return pd.Timestamp(x).strftime("%Y-%m-%d")


def main() -> None:
    panel, clima = load_inputs()
    df = build_features(panel, clima)
    s = temporal_split(df)
    thr = s.thresholds
    conjuntos = {"treino": s.train, "validação": s.val, "teste": s.test}

    linhas = []
    for nome, x in conjuntos.items():
        linhas.append((nome, d(x["week_start"].min()), d(x["week_start"].max()),
                       d(x["week_start"].min() + UMA), d(x["week_start"].max() + UMA),
                       x["week_start"].nunique(), len(x)))
    tab_split = pd.DataFrame(linhas, columns=["conjunto", "t inicial", "t final", "alvo inicial (t+1)",
                                              "alvo final (t+1)", "semanas", "linhas"])

    dist, rows = {}, []
    for nome, x in conjuntos.items():
        y = apply_thresholds(x["target_casos"], thr)
        dist[nome] = class_distribution(y)
        rows.append([nome] + [f"{dist[nome][c][0]} ({dist[nome][c][1]:.1f}%)" for c in config.CLASSES])
    tab_dist = pd.DataFrame(rows, columns=["conjunto"] + config.CLASSES)
    maior = max(
        ((abs(dist[n][c][1] - dist["treino"][c][1]), n, c) for n in ("validação", "teste") for c in config.CLASSES)
    )

    metricas = {n: persistence_baseline(x, thr) for n, x in conjuntos.items() if n != "treino"}
    tab_met = pd.DataFrame([
        [n, f"{m['f1_macro']:.3f}", f"{m['balanced_accuracy']:.3f}", f"{m['recall_baixo']:.3f}",
         f"{m['recall_medio']:.3f}", f"{m['recall_alto']:.3f}"] for n, m in metricas.items()
    ], columns=["conjunto", "F1-macro", "balanced accuracy", "recall baixo", "recall médio", "recall alto"])

    folds = expanding_window_splits(s.train)
    linhas_f = []
    for i, f in enumerate(folds, 1):
        tr, va = s.train.iloc[f.train_idx], s.train.iloc[f.valid_idx]
        dist_f = class_distribution(f.y_valid)
        linhas_f.append([i, f"{d(tr['week_start'].min())} a {d(tr['week_start'].max())}", len(tr),
                         f"{d(va['week_start'].min())} a {d(va['week_start'].max())}", len(va),
                         f"({f.thresholds[0]:g}, {f.thresholds[1]:g})",
                         f"{dist_f['baixo'][1]:.0f}/{dist_f['medio'][1]:.0f}/{dist_f['alto'][1]:.0f}"])
    tab_folds = pd.DataFrame(linhas_f, columns=["fold", "treino (t)", "linhas treino", "validação (t)",
                                                "linhas validação", "limiares do fold", "% baixo/médio/alto na validação"])

    out = ["# Resumo do split temporal", "",
           f"Dados: {len(df)} linhas (bairro x semana) de {d(df['week_start'].min())} a {d(df['week_start'].max())}, "
           f"{df['bairro'].nunique()} bairros, {len(feature_columns())} features. As {config.MAX_HISTORY_WEEKS} primeiras "
           "semanas do painel foram descartadas (histórico incompleto) e a última semana não tem alvo.", "",
           "## Conjuntos", "",
           f"Cada linha t tem features até a semana t e alvo na semana t+1. Entre os conjuntos há {config.GAP_WEEKS} "
           "semana(s) de linhas excluídas, de modo que o alvo da última linha de um conjunto cai antes da primeira "
           "linha do seguinte.", "", md_table(tab_split), "",
           "## Limiares de risco (ajustados só nos alvos do treino)", "",
           f"- Quantil {config.Q_MID}: **{thr[0]:g}** casos/semana/bairro",
           f"- Quantil {config.Q_HIGH}: **{thr[1]:g}** casos/semana/bairro",
           "- Regra: baixo = casos <= q_mid; médio = casos <= q_high; alto = acima.", ""]
    if thr[0] == 0:
        out += ["> O limiar de baixo risco é 0: a classe 'baixo' significa nenhum caso.", ""]
    out += ["## Distribuição de classes (alvo t+1, com os limiares do treino)", "", md_table(tab_dist), ""]
    if maior[0] >= 5:
        out += [f"> **Atenção:** a distribuição muda bastante entre conjuntos. A maior diferença para o treino é "
                f"{maior[0]:.1f} pontos percentuais (classe '{maior[2]}' no conjunto '{maior[1]}'). Métricas de validação e de "
                "teste não são comparáveis entre si sem levar isso em conta.", ""]
    out += ["## Baseline de persistência (classe de casos(t) repetida em t+1, mesmos limiares)", "",
            md_table(tab_met), ""]
    for n, m in metricas.items():
        out += [f"Matriz de confusão, {n} (linhas = real, colunas = previsto; baixo, médio, alto):", "",
                "```", *[str(r) for r in m["confusion_matrix"]], "```", ""]
    out += [f"## CV de janela expansiva ({config.CV_SPLITS} splits, só dentro do treino)", "",
            "Os limiares de cada fold usam só os alvos do treino daquele fold.", "", md_table(tab_folds), ""]
    raras = [(i, c) for i, f in enumerate(folds, 1) for c in config.CLASSES
             if class_distribution(f.y_valid)[c][1] < 1.0]
    if raras:
        out += ["> **Atenção:** " + "; ".join(f"no fold {i} a classe '{c}' tem menos de 1% da validação" for i, c in raras)
                + ". O fold 1 treina só na epidemia de 2015-2016, então seus limiares (altos) deixam quase nada "
                "como 'alto' depois; a F1-macro desse fold é pouco informativa.", ""]
    config.REPORTS_DIR.mkdir(exist_ok=True)
    (config.REPORTS_DIR / "split_resumo.md").write_text("\n".join(out), encoding="utf-8")
    print(tab_split.to_string(index=False))
    print(thr)
    print(tab_dist.to_string(index=False))
    print(tab_met.to_string(index=False))


if __name__ == "__main__":
    main()
