"""Experimento 03: ablação de features, busca de hiperparâmetros, escolha do modelo final e diagnóstico.

A busca usa a CV de janela expansiva com limiares de rótulo FIXOS (ajustados no treino inteiro),
porque o RandomizedSearchCV exige um y único. Limitação: os limiares fixos usam alvos de semanas que,
em cada fold, pertencem à validação do fold. A seleção usa a média do F1-macro nos folds 2 a 5.
O conjunto de teste continua bloqueado (LockedSplit).
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, make_scorer
from sklearn.model_selection import RandomizedSearchCV

from src import config
from src.evaluate import compute_metrics, persistence_baseline
from src.features import feature_columns
from src.labels import apply_thresholds
from src.models import DISPLAY_NAMES, build_model, search_space
from src.reporting import (FOLDS_NA_MEDIA, md_table, plot_confusion, plot_learning_curve, plot_roc, predict_proba_full,
                           roc_data)
from src.tracking import Tracker
from src.train import LockedSplit, locked_split
from src.validation import expanding_window_splits

SCORER = make_scorer(f1_score, labels=[0, 1, 2], average="macro", zero_division=0)
TUNED = ("rf", "logreg")
LEARNING_FRACTIONS = (0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
IDX_FOLDS_2_5 = [k - 1 for k in FOLDS_NA_MEDIA]


def f1_macro(y_true, y_pred) -> float:
    return float(f1_score(y_true, y_pred, labels=[0, 1, 2], average="macro", zero_division=0))


def clean_params(params: dict) -> dict:
    limpo = {}
    for k, v in params.items():
        if isinstance(v, np.generic):
            v = v.item()
        limpo[k] = v
    return limpo


def ablation(train_df: pd.DataFrame, folds) -> dict:
    """RandomForest padrão na CV (folds 2 a 5, limiares fixos): conjunto atual x conjunto + features da cidade.

    Regra: se a diferença média for menor que o desvio entre folds (desvio amostral do F1 do conjunto atual),
    mantém-se o conjunto mais simples (atual).
    """
    scores = {}
    for nome, city in (("base", False), ("base+cidade", True)):
        cols = feature_columns(city)
        X = train_df[cols]
        por_fold = []
        for i, f in enumerate(folds, 1):
            if i not in FOLDS_NA_MEDIA:
                continue
            modelo = build_model("rf").fit(X.iloc[f.train_idx], f.y_train)
            por_fold.append(f1_macro(f.y_valid, modelo.predict(X.iloc[f.valid_idx])))
        scores[nome] = por_fold
    base, cidade = np.array(scores["base"]), np.array(scores["base+cidade"])
    dif = float(cidade.mean() - base.mean())
    desvio = float(base.std(ddof=1))
    if dif > desvio:
        escolha, motivo = "base+cidade", "a diferença média supera o desvio entre folds"
    elif dif < -desvio:
        escolha, motivo = "base", "o conjunto atual é claramente melhor (diferença negativa maior que o desvio entre folds)"
    else:
        escolha, motivo = "base", "diferença menor que o desvio entre folds: mantém-se o conjunto mais simples"
    return {
        "folds": list(FOLDS_NA_MEDIA),
        "f1_base_por_fold": base.tolist(),
        "f1_cidade_por_fold": cidade.tolist(),
        "f1_base_media": float(base.mean()),
        "f1_cidade_media": float(cidade.mean()),
        "diferenca_media": dif,
        "desvio_entre_folds_base": desvio,
        "desvio_das_diferencas_pareadas": float((cidade - base).std(ddof=1)),
        "conjunto_escolhido": escolha,
        "motivo": motivo,
        "n_features_base": len(feature_columns(False)),
        "n_features_cidade": len(feature_columns(True)),
    }


def select_by_folds_2_5(cv_results: dict) -> int:
    medias = np.mean([cv_results[f"split{i}_test_score"] for i in IDX_FOLDS_2_5], axis=0)
    return int(np.argmax(medias))


def run_search(name: str, train_df: pd.DataFrame, folds, features: list[str], thresholds, n_iter: int):
    """RandomizedSearchCV com as divisões expansivas e seleção pela média dos folds 2 a 5."""
    X = train_df[features]
    y = apply_thresholds(train_df["target_casos"], thresholds)
    cv = [(f.train_idx, f.valid_idx) for f in folds]
    busca = RandomizedSearchCV(build_model(name), search_space(name), n_iter=n_iter, scoring=SCORER, cv=cv,
                               refit=select_by_folds_2_5, random_state=config.SEED, n_jobs=1, error_score="raise")
    inicio = time.perf_counter()
    busca.fit(X, y)
    segundos = time.perf_counter() - inicio
    res = busca.cv_results_
    n_folds = len(folds)
    tabela = pd.DataFrame({
        "modelo": DISPLAY_NAMES[name],
        "candidato": range(len(res["params"])),
        "params": [json.dumps(clean_params(p), default=str) for p in res["params"]],
        **{f"f1_fold{i + 1}": res[f"split{i}_test_score"] for i in range(n_folds)},
    })
    folds_2_5 = tabela[[f"f1_fold{k}" for k in FOLDS_NA_MEDIA]]
    tabela["f1_cv_media_f2_5"] = folds_2_5.mean(axis=1)
    tabela["f1_cv_desvio_f2_5"] = folds_2_5.std(axis=1, ddof=1)
    tabela["rank"] = tabela["f1_cv_media_f2_5"].rank(ascending=False, method="min").astype(int)
    return busca, tabela, segundos


def evaluate_on_validation(model, split: LockedSplit, features: list[str]) -> dict:
    thr = split.thresholds
    X_tr, X_va = split.train[features], split.val[features]
    y_tr = apply_thresholds(split.train["target_casos"], thr)
    y_va = apply_thresholds(split.val["target_casos"], thr)
    m_train = compute_metrics(y_tr, model.predict(X_tr))
    m_val = compute_metrics(y_va, model.predict(X_va))
    roc = roc_data(y_va, predict_proba_full(model, X_va))
    return {"train": m_train, "val": m_val, "roc": roc}


def learning_curve_table(name: str, params: dict, split: LockedSplit, features: list[str]) -> pd.DataFrame:
    """F1-macro de treino x validação ao treinar com as primeiras k semanas do treino (limiares fixos)."""
    thr = split.thresholds
    semanas = sorted(split.train["week_start"].unique())
    X_va = split.val[features]
    y_va = apply_thresholds(split.val["target_casos"], thr)
    linhas = []
    for frac in LEARNING_FRACTIONS:
        k = max(4, int(round(frac * len(semanas))))
        sub = split.train[split.train["week_start"] <= semanas[k - 1]]
        y_sub = apply_thresholds(sub["target_casos"], thr)
        modelo = build_model(name, params).fit(sub[features], y_sub)
        f_tr = f1_macro(y_sub, modelo.predict(sub[features]))
        f_va = f1_macro(y_va, modelo.predict(X_va))
        linhas.append({"fracao": frac, "semanas_treino": k, "linhas_treino": len(sub), "f1_macro_treino": f_tr,
                       "f1_macro_val": f_va, "gap_treino_val": f_tr - f_va})
    return pd.DataFrame(linhas)


def choose_final(candidatos: list[dict], persistencia_val_f1: float) -> dict:
    """Maior F1-macro médio na CV (folds 2 a 5), confirmado na validação.

    Confirmado = F1 da validação acima da persistência e no máximo 0,01 abaixo do outro candidato.
    """
    ordenados = sorted(candidatos, key=lambda c: c["cv_f1_media_f2_5"], reverse=True)
    escolhido, outros = ordenados[0], ordenados[1:]
    melhor_val_outros = max((o["val_f1_macro"] for o in outros), default=-1.0)
    acima_persistencia = escolhido["val_f1_macro"] > persistencia_val_f1
    nao_pior_que_outro = escolhido["val_f1_macro"] >= melhor_val_outros - 0.01
    confirmado = bool(acima_persistencia and nao_pior_que_outro)
    justificativa = [
        f"{escolhido['display']} tem o maior F1-macro médio na CV (folds 2 a 5): {escolhido['cv_f1_media_f2_5']:.3f}"
        + "".join(f" contra {o['display']} {o['cv_f1_media_f2_5']:.3f}" for o in outros) + ".",
        f"Na validação o F1-macro dele é {escolhido['val_f1_macro']:.3f} (persistência: {persistencia_val_f1:.3f}"
        + "".join(f"; {o['display']}: {o['val_f1_macro']:.3f}" for o in outros) + ").",
        "Confirmado na validação." if confirmado else
        "ATENÇÃO: a validação NÃO confirma por completo a escolha da CV (ver números acima); "
        "a decisão segue a regra combinada (CV) mas deve ser lida com cautela.",
    ]
    return {**escolhido, "validacao_confirma": confirmado, "justificativa": justificativa}


def update_comparison_csv(path: Path, novas: list[dict], experimento: str = "03") -> pd.DataFrame:
    """Acrescenta as linhas do experimento 03 a metricas_comparacao.csv (substitui as do 03 já existentes)."""
    antigo = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if "experimento" not in antigo.columns:
        antigo["experimento"] = "02"
    antigo = antigo[antigo["experimento"] != experimento]
    novo = pd.DataFrame(novas).assign(experimento=experimento)
    tabela = pd.concat([antigo, novo], ignore_index=True)
    tabela.to_csv(path, index=False)
    return tabela


def row_from_metrics(label: str, m: dict, cv_media: float, cv_f1: float, cv_recall_alto: float, auc_val: float,
                     fit_segundos: float) -> dict:
    return {
        "modelo": label,
        "f1_macro_cv_f2_5": cv_media,
        "f1_macro_cv_f1": cv_f1,
        "recall_alto_cv_f2_5": cv_recall_alto,
        "f1_macro_treino": m["train"]["f1_macro"],
        "f1_macro_val": m["val"]["f1_macro"],
        "balanced_accuracy_val": m["val"]["balanced_accuracy"],
        "recall_alto_val": m["val"]["recall_alto"],
        "auc_macro_val": auc_val,
        "gap_treino_val": m["train"]["f1_macro"] - m["val"]["f1_macro"],
        "gap_treino_cv": m["train"]["f1_macro"] - cv_media,
        "fit_segundos": fit_segundos,
        "cv_segundos": float("nan"),
    }


def run_exp03(df: pd.DataFrame, tracker: Tracker, n_iter: int, reports_dir: Path, figures_dir: Path,
              choice_path: Path, models_to_tune: tuple[str, ...] = TUNED) -> dict:
    """Ablação, busca (RF e LogisticRegression), escolha do modelo e diagnóstico. Não toca no teste."""
    split = locked_split(df)
    thr = split.thresholds
    folds = expanding_window_splits(split.train, thresholds=thr)
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    abl = ablation(split.train, folds)
    features = feature_columns(abl["conjunto_escolhido"] == "base+cidade")
    print(f"Ablação: base {abl['f1_base_media']:.3f} x base+cidade {abl['f1_cidade_media']:.3f} "
          f"(dif {abl['diferenca_media']:+.3f}, desvio entre folds {abl['desvio_entre_folds_base']:.3f}) -> "
          f"{abl['conjunto_escolhido']}")
    with tracker.run("ablacao-features", {"tipo": "ablacao"}):
        tracker.log_params({"modelo": "RandomForest (padrão)", "cv": "expanding, folds 2-5, limiares fixos",
                            "conjunto_escolhido": abl["conjunto_escolhido"], "motivo": abl["motivo"]})
        tracker.log_metrics({"f1_base_media": abl["f1_base_media"], "f1_cidade_media": abl["f1_cidade_media"],
                             "diferenca_media": abl["diferenca_media"],
                             "desvio_entre_folds_base": abl["desvio_entre_folds_base"]})
        tracker.log_dict(abl, "ablacao_features.json")
    (reports_dir / "ablacao_features.json").write_text(json.dumps(abl, indent=2, ensure_ascii=False), encoding="utf-8")

    pers_val = persistence_baseline(split.val, thr)
    pers_cv = []
    for f in folds:
        pers_cv.append(persistence_baseline(split.train.iloc[f.valid_idx], thr))
    y_tr_full = apply_thresholds(split.train["target_casos"], thr)

    candidatos, tabelas, linhas_csv, buscas = [], [], [], {}
    for name in models_to_tune:
        busca, tabela, segundos = run_search(name, split.train, folds, features, thr, n_iter)
        buscas[name] = busca
        tabelas.append(tabela)
        melhor = busca.best_estimator_
        params = clean_params(busca.best_params_)
        mv = evaluate_on_validation(melhor, split, features)
        melhor_linha = tabela.loc[tabela["rank"].idxmin()]
        cv_media = float(melhor_linha["f1_cv_media_f2_5"])
        cand = {
            "name": name, "display": DISPLAY_NAMES[name], "best_params": params, "cv_f1_media_f2_5": cv_media,
            "cv_f1_desvio_f2_5": float(melhor_linha["f1_cv_desvio_f2_5"]), "cv_f1_fold1": float(melhor_linha["f1_fold1"]),
            "val_f1_macro": mv["val"]["f1_macro"], "val_recall_alto": mv["val"]["recall_alto"],
            "val_auc_macro": mv["roc"]["auc_macro"], "train_f1_macro": mv["train"]["f1_macro"],
            "search_seconds": segundos, "n_iter": n_iter,
        }
        candidatos.append(cand)
        print(f"{DISPLAY_NAMES[name]}: busca {segundos:.0f}s, melhor CV f2-5={cv_media:.3f}, val={cand['val_f1_macro']:.3f}, "
              f"params={params}")

        f_cm = figures_dir / f"cm_{name}_otimizado.png"
        f_roc = figures_dir / f"roc_{name}_otimizado.png"
        plot_confusion(mv["val"]["confusion_matrix"], f"{DISPLAY_NAMES[name]} otimizado — validação", f_cm)
        plot_roc(mv["roc"], f"{DISPLAY_NAMES[name]} otimizado — validação", f_roc)
        csv_busca = reports_dir / f"busca_{name}.csv"
        tabela.to_csv(csv_busca, index=False)

        with tracker.run(f"{DISPLAY_NAMES[name]}-busca", {"tipo": "busca", "experimento": config.EXP_TUNING}):
            tracker.log_params({
                "modelo": DISPLAY_NAMES[name], "n_iter": n_iter, "scoring": "f1_macro",
                "cv": "janela expansiva, 5 folds, limiares fixos do treino",
                "selecao": "media do F1-macro nos folds 2 a 5",
                "limiar_q_mid": thr[0], "limiar_q_high": thr[1], "conjunto_features": abl["conjunto_escolhido"],
                "n_features": len(features), "seed": config.SEED, "melhores_parametros": json.dumps(params, default=str),
                **{f"melhor_{k}": v for k, v in params.items()},
            })
            tracker.log_metrics({
                "melhor_cv_f1_media_f2_5": cv_media, "melhor_cv_f1_desvio_f2_5": cand["cv_f1_desvio_f2_5"],
                "melhor_cv_f1_fold1": cand["cv_f1_fold1"], "val_f1_macro": cand["val_f1_macro"],
                "val_recall_alto": cand["val_recall_alto"], "val_auc_macro": cand["val_auc_macro"],
                "train_f1_macro": cand["train_f1_macro"], "busca_segundos": segundos,
                "gap_treino_val": cand["train_f1_macro"] - cand["val_f1_macro"],
            })
            for _, linha in tabela.iterrows():
                with tracker.run(f"{name}-candidato-{int(linha['candidato']):02d}", nested=True):
                    tracker.log_params({"modelo": DISPLAY_NAMES[name], **json.loads(linha["params"])})
                    tracker.log_metrics({**{f"f1_fold{k}": linha[f"f1_fold{k}"] for k in range(1, len(folds) + 1)},
                                         "f1_cv_media_f2_5": linha["f1_cv_media_f2_5"],
                                         "f1_cv_desvio_f2_5": linha["f1_cv_desvio_f2_5"], "rank": linha["rank"]})
            tracker.log_dict({"confusion_matrix_val": mv["val"]["confusion_matrix"], "classes": config.CLASSES},
                             "confusion_matrix_val.json")
            for p in (f_cm, f_roc, csv_busca):
                tracker.log_artifact(p)

        pers_cv_f1 = float(np.mean([pers_cv[k - 1]["f1_macro"] for k in FOLDS_NA_MEDIA]))
        linhas_csv.append(row_from_metrics(
            f"{DISPLAY_NAMES[name]} (otimizado)", mv, cv_media, float(melhor_linha["f1_fold1"]),
            float("nan"), mv["roc"]["auc_macro"], segundos))
        cand["pers_cv_f1"] = pers_cv_f1

    escolha = choose_final(candidatos, pers_val["f1_macro"])
    escolha["conjunto_features"] = abl["conjunto_escolhido"]
    escolha["features"] = features
    escolha["thresholds"] = list(thr)
    escolha["persistencia_val_f1_macro"] = pers_val["f1_macro"]
    escolha["candidatos"] = candidatos

    curva = learning_curve_table(escolha["name"], escolha["best_params"], split, features)
    f_curva = figures_dir / "curva_aprendizado_final.png"
    plot_learning_curve(curva, f"{escolha['display']} otimizado: F1-macro por tamanho de treino", f_curva)
    curva.to_csv(reports_dir / "curva_aprendizado_final.csv", index=False)
    gap_final = float(curva.iloc[-1]["gap_treino_val"])
    escolha["gap_treino_val"] = gap_final
    escolha["diagnostico"] = _diagnostico(curva)

    choice_path.write_text(json.dumps(escolha, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with tracker.run("escolha-e-diagnostico", {"tipo": "escolha"}):
        tracker.log_params({"modelo_escolhido": escolha["display"], "validacao_confirma": escolha["validacao_confirma"],
                            "melhores_parametros": json.dumps(escolha["best_params"], default=str)})
        tracker.log_metrics({"cv_f1_media_f2_5": escolha["cv_f1_media_f2_5"], "val_f1_macro": escolha["val_f1_macro"],
                             "gap_treino_val": gap_final})
        tracker.log_dict({"justificativa": escolha["justificativa"], "diagnostico": escolha["diagnostico"]},
                         "justificativa.json")
        tracker.log_artifact(f_curva)
        tracker.log_artifact(reports_dir / "curva_aprendizado_final.csv")

    update_comparison_csv(reports_dir / "metricas_comparacao.csv", linhas_csv)
    write_summary(reports_dir / "otimizacao_resumo.md", abl, tabelas, candidatos, escolha, curva, pers_val, thr,
                  n_iter)
    return escolha


def _diagnostico(curva: pd.DataFrame) -> str:
    ultimo = curva.iloc[-1]
    gap, val = ultimo["gap_treino_val"], ultimo["f1_macro_val"]
    gap_inicial = curva.iloc[0]["gap_treino_val"]
    partes = [f"Com todo o treino: F1 treino {ultimo['f1_macro_treino']:.3f}, validação {val:.3f}, gap {gap:.3f}."]
    if gap > 0.10:
        partes.append("Gap grande: sinal claro de overfitting (o modelo decora o treino).")
    elif gap > 0.05:
        partes.append("Gap moderado: algum overfitting.")
    else:
        partes.append("Gap pequeno: sem overfitting relevante.")
    if ultimo["f1_macro_treino"] < 0.65 and val < 0.65:
        partes.append("F1 baixo também no treino: o modelo é limitado pelas features/ruído (underfitting ou teto de informação).")
    if curva["f1_macro_val"].iloc[-1] - curva["f1_macro_val"].iloc[-3] < 0.01:
        partes.append("A validação quase não melhora nas últimas frações: mais dados do mesmo tipo ajudam pouco.")
    partes.append(f"Gap com a menor fração de treino: {gap_inicial:.3f}.")
    return " ".join(partes)


def write_summary(path: Path, abl: dict, tabelas: list[pd.DataFrame], candidatos: list[dict], escolha: dict,
                  curva: pd.DataFrame, pers_val: dict, thr, n_iter: int) -> None:
    out = ["# Experimento 03: otimização de hiperparâmetros", "",
           f"Limiares de rótulo fixos do treino: ({thr[0]:g}, {thr[1]:g}). **Limitação:** o RandomizedSearchCV exige um "
           "y único, então a CV usa esses limiares fixos (calculados com o treino inteiro) em todos os folds; "
           "em cada fold isso inclui alvos que seriam da validação do fold na definição das classes. "
           "Seleção: média do F1-macro nos folds 2 a 5. O conjunto de teste não foi usado.", "",
           "## Ablação de features (RandomForest padrão, CV folds 2 a 5)", "",
           md_table(pd.DataFrame({
               "fold": abl["folds"],
               f"F1 base ({abl['n_features_base']} features)": [f"{v:.3f}" for v in abl["f1_base_por_fold"]],
               f"F1 base+cidade ({abl['n_features_cidade']} features)": [f"{v:.3f}" for v in abl["f1_cidade_por_fold"]],
           })), "",
           f"- Média base: **{abl['f1_base_media']:.3f}**; média base+cidade: **{abl['f1_cidade_media']:.3f}**; "
           f"diferença **{abl['diferenca_media']:+.3f}**.",
           f"- Desvio entre folds (conjunto base): {abl['desvio_entre_folds_base']:.3f}; desvio das diferenças "
           f"pareadas: {abl['desvio_das_diferencas_pareadas']:.3f}.",
           f"- Decisão: **{abl['conjunto_escolhido']}** ({abl['motivo']}).", "",
           f"## Busca de hiperparâmetros (n_iter = {n_iter} por modelo)", ""]
    for c, t in zip(candidatos, tabelas):
        top = t.sort_values("rank").head(5)[["rank", "f1_cv_media_f2_5", "f1_cv_desvio_f2_5", "f1_fold1", "params"]]
        top = top.assign(**{col: top[col].map(lambda v: f"{v:.3f}") for col in
                            ("f1_cv_media_f2_5", "f1_cv_desvio_f2_5", "f1_fold1")})
        out += [f"### {c['display']} (busca em {c['search_seconds']:.0f} s)", "",
                f"Melhores parâmetros: `{json.dumps(c['best_params'], default=str)}`", "", "Top 5 candidatos:", "",
                md_table(top), ""]
    tabela_c = pd.DataFrame([{
        "modelo": c["display"], "F1 CV f2–5": f"{c['cv_f1_media_f2_5']:.3f}", "F1 validação": f"{c['val_f1_macro']:.3f}",
        "recall alto val": f"{c['val_recall_alto']:.3f}", "AUC macro val": f"{c['val_auc_macro']:.3f}",
        "F1 treino": f"{c['train_f1_macro']:.3f}"} for c in candidatos])
    out += ["## Escolha do modelo final", "", md_table(tabela_c), "",
            f"Persistência na validação: F1-macro {pers_val['f1_macro']:.3f}, recall alto {pers_val['recall_alto']:.3f}.", "",
            *[f"- {j}" for j in escolha["justificativa"]], "",
            "## Overfitting e underfitting do modelo final", "", escolha["diagnostico"], "",
            md_table(curva.assign(**{c: curva[c].map(lambda v: f"{v:.3f}") for c in
                                     ("f1_macro_treino", "f1_macro_val", "gap_treino_val")})), "",
            "![curva](figuras/curva_aprendizado_final.png)", ""]
    path.write_text("\n".join(out), encoding="utf-8")
