"""Avaliação final: reajuste em treino+validação, uma única avaliação no teste, bootstrap e registro do modelo.

O teste só é aberto aqui, uma vez, com o modelo já escolhido no experimento 03. Se reports/teste_final.json
existir, a execução é recusada (a menos que force_reeval=True), porque reavaliar o teste invalida a conclusão.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from src import config
from src.evaluate import compute_metrics, persistence_baseline
from src.labels import apply_thresholds
from src.models import build_model
from src.reporting import md_table, plot_confusion, plot_roc, predict_proba_full, roc_data
from src.tracking import Tracker
from src.validation import temporal_split

META_FIELDS = ("sklearn_version", "model_name", "best_params", "thresholds", "classes", "features", "train_period",
               "validation_metrics", "test_metrics", "mlflow_run_id", "trained_at")


class FinalAlreadyEvaluated(RuntimeError):
    pass


def week_confusions(y_true: np.ndarray, y_pred: np.ndarray, weeks: np.ndarray, unique_weeks: np.ndarray) -> np.ndarray:
    """Matrizes de confusão 3x3 por semana (índice na ordem de unique_weeks)."""
    out = np.zeros((len(unique_weeks), 3, 3), dtype=np.int64)
    pos = np.searchsorted(unique_weeks, weeks)
    np.add.at(out, (pos, y_true, y_pred), 1)
    return out


def f1_macro_from_cm(cm: np.ndarray) -> float:
    tp = np.diag(cm).astype(float)
    pred = cm.sum(axis=0).astype(float)
    real = cm.sum(axis=1).astype(float)
    denom = pred + real
    f1 = np.where(denom > 0, 2 * tp / np.where(denom > 0, denom, 1), 0.0)
    return float(f1.mean())


def recall_alto_from_cm(cm: np.ndarray) -> float:
    real = cm[2].sum()
    return float(cm[2, 2] / real) if real > 0 else float("nan")


def block_bootstrap(cm_model: np.ndarray, cm_pers: np.ndarray, block: int, resamples: int, seed: int) -> dict:
    """Bootstrap por blocos móveis de semanas (preserva a autocorrelação temporal).

    Reamostra blocos de `block` semanas consecutivas com reposição, soma as matrizes de confusão e calcula a
    diferença modelo - persistência em F1-macro e recall da classe alto.
    """
    rng = np.random.default_rng(seed)
    n = cm_model.shape[0]
    block = max(1, min(block, n))
    n_blocks = int(np.ceil(n / block))
    dif_f1, dif_rec, f1_m, f1_p = [], [], [], []
    for _ in range(resamples):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        cm_m, cm_p = cm_model[idx].sum(axis=0), cm_pers[idx].sum(axis=0)
        a, b = f1_macro_from_cm(cm_m), f1_macro_from_cm(cm_p)
        f1_m.append(a)
        f1_p.append(b)
        dif_f1.append(a - b)
        dif_rec.append(recall_alto_from_cm(cm_m) - recall_alto_from_cm(cm_p))
    dif_f1, dif_rec = np.array(dif_f1), np.array(dif_rec)
    dif_rec = dif_rec[~np.isnan(dif_rec)]
    return {
        "block_weeks": block,
        "resamples": resamples,
        "f1_diff_mean": float(dif_f1.mean()),
        "f1_diff_ci95": [float(np.percentile(dif_f1, 2.5)), float(np.percentile(dif_f1, 97.5))],
        "f1_model_ci95": [float(np.percentile(f1_m, 2.5)), float(np.percentile(f1_m, 97.5))],
        "f1_persistence_ci95": [float(np.percentile(f1_p, 2.5)), float(np.percentile(f1_p, 97.5))],
        "prob_f1_diff_gt0": float((dif_f1 > 0).mean()),
        "recall_alto_diff_mean": float(dif_rec.mean()) if len(dif_rec) else float("nan"),
        "recall_alto_diff_ci95": ([float(np.percentile(dif_rec, 2.5)), float(np.percentile(dif_rec, 97.5))]
                                  if len(dif_rec) else [float("nan"), float("nan")]),
    }


def conclusion_text(boot: dict, f1_model: float, f1_pers: float) -> str:
    lo, hi = boot["f1_diff_ci95"]
    dif = f1_model - f1_pers
    if lo > 0:
        return (f"O modelo supera a persistência de forma estatisticamente convincente: diferença de F1-macro "
                f"{dif:+.3f}, IC95% [{lo:+.3f}, {hi:+.3f}] exclui zero (bloco de {boot['block_weeks']} semanas).")
    if hi < 0:
        return (f"O modelo é PIOR que a persistência: diferença de F1-macro {dif:+.3f}, IC95% [{lo:+.3f}, {hi:+.3f}] "
                f"fica abaixo de zero.")
    return (f"NÃO há evidência estatística convincente de que o modelo supere a persistência: diferença de F1-macro "
            f"{dif:+.3f}, IC95% [{lo:+.3f}, {hi:+.3f}] inclui zero (probabilidade de diferença > 0 no bootstrap: "
            f"{boot['prob_f1_diff_gt0']:.2f}).")


def build_meta(choice: dict, features: list[str], train_period: dict, val_metrics: dict, test_metrics: dict,
               run_id: str | None) -> dict:
    return {
        "sklearn_version": sklearn.__version__,
        "model_name": choice["display"],
        "best_params": choice["best_params"],
        "thresholds": list(choice["thresholds"]),
        "classes": config.CLASSES,
        "features": features,
        "train_period": train_period,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "mlflow_run_id": run_id,
        "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }


def run_final(df: pd.DataFrame, tracker: Tracker, force_reeval: bool = False, choice_path: Path = config.CHOICE_PATH,
              final_path: Path = config.FINAL_TEST_PATH, model_path: Path = config.MODEL_PATH,
              meta_path: Path = config.MODEL_META_PATH, reports_dir: Path = config.REPORTS_DIR,
              figures_dir: Path | None = None, resamples: int = config.BOOTSTRAP_RESAMPLES) -> dict:
    if final_path.exists() and not force_reeval:
        raise FinalAlreadyEvaluated(
            f"{final_path.name} já existe: o teste já foi avaliado. Reavaliar o teste invalida a conclusão "
            "(o modelo passaria a ser ajustado olhando o teste). Use --force-reeval só se for realmente necessário."
        )
    if not choice_path.exists():
        raise FileNotFoundError(f"{choice_path.name} não existe: rode antes o experimento 03 (--exp 03).")
    if final_path.exists():
        print("AVISO: --force-reeval: reavaliar o teste invalida a conclusão anterior.")
    figures_dir = figures_dir or reports_dir / "figuras"
    figures_dir.mkdir(parents=True, exist_ok=True)

    choice = json.loads(choice_path.read_text(encoding="utf-8"))
    features = choice["features"]
    split = temporal_split(df)
    thr = tuple(choice["thresholds"])
    if tuple(split.thresholds) != thr:
        raise ValueError("os limiares do split atual diferem dos usados na escolha do modelo; rode --exp 03 de novo")

    trainval = pd.concat([split.train, split.val], ignore_index=True)
    y_tv = apply_thresholds(trainval["target_casos"], thr)
    model = build_model(choice["name"], choice["best_params"]).fit(trainval[features], y_tv)

    test = split.test
    y_te = apply_thresholds(test["target_casos"], thr)
    pred = model.predict(test[features])
    m_test = compute_metrics(y_te, pred)
    proba = predict_proba_full(model, test[features])
    roc = roc_data(y_te, proba)
    m_pers = persistence_baseline(test, thr)
    pred_pers = apply_thresholds(test["casos_t"], thr)

    weeks = test["week_start"].to_numpy()
    uw = np.unique(weeks)
    cm_m = week_confusions(np.asarray(y_te), np.asarray(pred), weeks, uw)
    cm_p = week_confusions(np.asarray(y_te), np.asarray(pred_pers), weeks, uw)
    boot = {}
    for b in sorted({config.BOOTSTRAP_BLOCK_WEEKS, 1, 2}):
        boot[f"bloco_{b}"] = block_bootstrap(cm_m, cm_p, b, resamples, config.SEED)
    principal = boot[f"bloco_{config.BOOTSTRAP_BLOCK_WEEKS}"]
    conclusao = conclusion_text(principal, m_test["f1_macro"], m_pers["f1_macro"])

    dist = {nome: int((np.asarray(y_te) == i).sum()) for i, nome in enumerate(config.CLASSES)}
    resultado = {
        "modelo": choice["display"],
        "best_params": choice["best_params"],
        "thresholds": list(thr),
        "features": features,
        "periodo_teste": {"inicio": str(test["week_start"].min().date()), "fim": str(test["week_start"].max().date()),
                          "semanas": int(len(uw)), "linhas": int(len(test))},
        "distribuicao_classes_teste": dist,
        "modelo_teste": {**{k: v for k, v in m_test.items()}, "auc_macro": roc["auc_macro"],
                         "auc_por_classe": {n: roc["curves"][n][2] for n in config.CLASSES}},
        "persistencia_teste": m_pers,
        "diferenca_f1_macro": m_test["f1_macro"] - m_pers["f1_macro"],
        "diferenca_recall_alto": m_test["recall_alto"] - m_pers["recall_alto"],
        "bootstrap": boot,
        "conclusao": conclusao,
        "avaliado_em": pd.Timestamp.now(tz="UTC").isoformat(),
        "force_reeval": bool(force_reeval),
    }
    final_path.write_text(json.dumps(resultado, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    f_cm = figures_dir / "cm_final_teste.png"
    f_cm_p = figures_dir / "cm_persistencia_teste.png"
    f_roc = figures_dir / "roc_final_teste.png"
    plot_confusion(m_test["confusion_matrix"], f"{choice['display']} — teste", f_cm)
    plot_confusion(m_pers["confusion_matrix"], "Persistência — teste", f_cm_p)
    plot_roc(roc, f"{choice['display']} — teste (one-vs-rest)", f_roc)

    val_metrics = {"f1_macro": choice["val_f1_macro"], "recall_alto": choice["val_recall_alto"],
                   "auc_macro": choice["val_auc_macro"], "cv_f1_macro_media_f2_5": choice["cv_f1_media_f2_5"],
                   "ajustado_em": "treino (sem validação)"}
    pers_val = persistence_baseline(split.val, thr)
    val_metrics["persistencia_f1_macro"] = pers_val["f1_macro"]
    val_metrics["persistencia_recall_alto"] = pers_val["recall_alto"]
    test_metrics = {"f1_macro": m_test["f1_macro"], "balanced_accuracy": m_test["balanced_accuracy"],
                    "recall_alto": m_test["recall_alto"], "auc_macro": roc["auc_macro"],
                    "persistencia_f1_macro": m_pers["f1_macro"], "persistencia_recall_alto": m_pers["recall_alto"],
                    "f1_diff_ic95": principal["f1_diff_ci95"]}
    train_period = {"inicio": str(trainval["week_start"].min().date()), "fim": str(trainval["week_start"].max().date()),
                    "treino_fim_original": str(split.train["week_start"].max().date()),
                    "linhas": int(len(trainval)), "limiares_ajustados_em": "treino (sem validação)"}

    run_id, version = None, None
    with tracker.run("modelo-final", {"tipo": "final"}):
        run_id = tracker.run_id
        tracker.log_params({"modelo": choice["display"], "melhores_parametros": json.dumps(choice["best_params"],
                            default=str), "ajuste": "treino+validação", "limiares": str(thr)})
        tracker.log_metrics({"val_f1_macro": val_metrics["f1_macro"], "teste_f1_macro": m_test["f1_macro"],
                             "teste_recall_alto": m_test["recall_alto"], "teste_auc_macro": roc["auc_macro"],
                             "teste_persistencia_f1_macro": m_pers["f1_macro"],
                             "teste_diff_f1_macro": resultado["diferenca_f1_macro"],
                             "teste_diff_ic95_inf": principal["f1_diff_ci95"][0],
                             "teste_diff_ic95_sup": principal["f1_diff_ci95"][1]})
        for p in (f_cm, f_cm_p, f_roc, final_path):
            tracker.log_artifact(p)
        meta = build_meta(choice, features, train_period, val_metrics, test_metrics, run_id)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        tracker.log_artifact(meta_path)
        version = tracker.log_model(model, trainval[features].head(5), config.MLFLOW_MODEL_NAME)
        if version is not None:
            tracker.set_alias(config.MLFLOW_MODEL_NAME, config.CHAMPION_ALIAS, version)
    resultado["mlflow_run_id"] = run_id
    resultado["registry_version"] = version
    write_report(reports_dir / "teste_final.md", resultado)
    return resultado


def write_report(path: Path, r: dict) -> None:
    m, p, b = r["modelo_teste"], r["persistencia_teste"], r["bootstrap"]
    linhas = pd.DataFrame([
        {"métrica": "F1-macro", "modelo": f"{m['f1_macro']:.3f}", "persistência": f"{p['f1_macro']:.3f}"},
        {"métrica": "balanced accuracy", "modelo": f"{m['balanced_accuracy']:.3f}",
         "persistência": f"{p['balanced_accuracy']:.3f}"},
        {"métrica": "recall alto", "modelo": f"{m['recall_alto']:.3f}", "persistência": f"{p['recall_alto']:.3f}"},
        {"métrica": "AUC macro (OvR)", "modelo": f"{m['auc_macro']:.3f}", "persistência": "—"},
    ])
    boot_linhas = pd.DataFrame([{
        "bloco (semanas)": v["block_weeks"], "dif. F1 média": f"{v['f1_diff_mean']:+.3f}",
        "IC95% dif. F1": f"[{v['f1_diff_ci95'][0]:+.3f}, {v['f1_diff_ci95'][1]:+.3f}]",
        "P(dif>0)": f"{v['prob_f1_diff_gt0']:.2f}",
        "IC95% dif. recall alto": f"[{v['recall_alto_diff_ci95'][0]:+.3f}, {v['recall_alto_diff_ci95'][1]:+.3f}]",
    } for v in b.values()])
    texto = [
        "# Avaliação final no conjunto de teste", "",
        f"Modelo: **{r['modelo']}** (reajustado em treino+validação; limiares do treino {tuple(r['thresholds'])}). "
        f"Teste: {r['periodo_teste']['inicio']} a {r['periodo_teste']['fim']} ({r['periodo_teste']['semanas']} semanas, "
        f"{r['periodo_teste']['linhas']} linhas). Avaliado uma única vez.", "",
        f"Distribuição das classes no teste: {r['distribuicao_classes_teste']}", "",
        md_table(linhas), "",
        f"Diferença de F1-macro (modelo − persistência): **{r['diferenca_f1_macro']:+.3f}**.", "",
        "## Bootstrap por blocos de semanas (" + str(config.BOOTSTRAP_RESAMPLES) + " reamostragens)", "",
        md_table(boot_linhas), "", f"**Conclusão:** {r['conclusao']}", "",
        "![cm](figuras/cm_final_teste.png) ![cm pers](figuras/cm_persistencia_teste.png) "
        "![roc](figuras/roc_final_teste.png)", "",
    ]
    path.write_text("\n".join(texto), encoding="utf-8")
