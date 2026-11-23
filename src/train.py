"""Experimentos 01 (baseline) e 02 (comparação de modelos) no MLflow.

Treina no treino e avalia na validação; a CV usa as divisões de janela expansiva do passo 5.
O conjunto de teste é bloqueado: qualquer acesso levanta TestSetLocked.

Uso:
    python -m src.train --exp 01
    python -m src.train --exp 02
    python -m src.train --exp 02 --no-mlflow
"""
import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import auc, roc_curve

from src import config
from src.evaluate import compute_metrics, persistence_baseline
from src.features import build_features, feature_columns, load_inputs
from src.labels import apply_thresholds
from src.models import CLASS_WEIGHT_SUPPORT, DISPLAY_NAMES, NEEDS_SCALER, build_model, candidate_names
from src.tracking import Tracker
from src.validation import Split, expanding_window_splits, temporal_split

FIGURES_DIR = config.REPORTS_DIR / "figuras"
AZUL, LARANJA, CINZA, VERDE = "#2b6cb0", "#c2410c", "#6b7280", "#2f855a"
FOLDS_NA_MEDIA = (2, 3, 4, 5)
PERSISTENCE = "persistencia"
MODELO_LENTO_SEGUNDOS = 120


class TestSetLocked(RuntimeError):
    __test__ = False


class LockedSplit:
    """Split sem acesso ao teste: train, val e thresholds liberados; test levanta TestSetLocked."""

    def __init__(self, split: Split):
        self._split = split

    @property
    def train(self) -> pd.DataFrame:
        return self._split.train

    @property
    def val(self) -> pd.DataFrame:
        return self._split.val

    @property
    def thresholds(self) -> tuple[float, float]:
        return self._split.thresholds

    @property
    def test(self):
        raise TestSetLocked(
            "O conjunto de teste não pode ser usado nos experimentos 01 e 02. "
            "Ele só é avaliado uma vez, no final do projeto."
        )


def locked_split(df: pd.DataFrame, **kwargs) -> LockedSplit:
    return LockedSplit(temporal_split(df, **kwargs))


def predict_proba_full(model, X) -> np.ndarray:
    proba = model.predict_proba(X)
    full = np.zeros((len(X), len(config.CLASSES)))
    full[:, model.named_steps["clf"].classes_.astype(int)] = proba
    return full


def roc_data(y_true: np.ndarray, proba: np.ndarray) -> dict:
    """ROC one-vs-rest por classe e AUC macro (média das classes com positivos e negativos)."""
    curvas, aucs = {}, []
    for i, nome in enumerate(config.CLASSES):
        positivo = (y_true == i).astype(int)
        if positivo.sum() == 0 or positivo.sum() == len(positivo):
            curvas[nome] = (None, None, float("nan"))
            continue
        fpr, tpr, _ = roc_curve(positivo, proba[:, i])
        curvas[nome] = (fpr, tpr, auc(fpr, tpr))
        aucs.append(curvas[nome][2])
    return {"curves": curvas, "auc_macro": float(np.mean(aucs)) if aucs else float("nan")}


def plot_confusion(cm: list[list[int]], titulo: str, path: Path) -> None:
    cm = np.asarray(cm)
    norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(4.6, 4))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            cor = "white" if norm[i, j] > 0.55 else "#111827"
            ax.text(j, i, f"{cm[i, j]}\n{norm[i, j] * 100:.0f}%", ha="center", va="center", color=cor, fontsize=9)
    ax.set_xticks(range(3), config.CLASSES)
    ax.set_yticks(range(3), config.CLASSES)
    ax.set_xlabel("previsto")
    ax.set_ylabel("real")
    ax.set_title(titulo, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_roc(roc: dict, titulo: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    estilos = {"baixo": (AZUL, "-"), "medio": (LARANJA, "--"), "alto": (VERDE, ":")}
    for nome, (fpr, tpr, a) in roc["curves"].items():
        if fpr is not None:
            cor, ls = estilos[nome]
            ax.plot(fpr, tpr, color=cor, ls=ls, lw=2, label=f"{nome} (AUC {a:.2f})")
    ax.plot([0, 1], [0, 1], color=CINZA, lw=1)
    ax.set_xlabel("falsos positivos")
    ax.set_ylabel("verdadeiros positivos")
    ax.set_title(f"{titulo}\nAUC macro {roc['auc_macro']:.2f}", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def grouped_bars(tabela: pd.DataFrame, colunas: dict[str, str], titulo: str, path: Path, ylabel: str) -> None:
    """Barras agrupadas por modelo. colunas: {coluna da tabela: rótulo na legenda}."""
    cores = [AZUL, LARANJA, CINZA]
    x = np.arange(len(tabela))
    largura = 0.8 / len(colunas)
    fig, ax = plt.subplots(figsize=(max(6.5, 1.3 * len(tabela)), 4.2))
    for k, (col, rotulo) in enumerate(colunas.items()):
        barras = ax.bar(x + (k - (len(colunas) - 1) / 2) * largura, tabela[col], largura, color=cores[k], label=rotulo)
        for b, v in zip(barras, tabela[col]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x, tabela["modelo"], rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo, fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e7eb", lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_importance(imp: pd.DataFrame, path: Path) -> None:
    imp = imp.sort_values("importancia")
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.barh(imp["feature"], imp["importancia"], color=AZUL)
    ax.set_xlabel("importância (RandomForest)")
    ax.set_title("Importância das features", fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def cv_scores(name: str, train_df: pd.DataFrame, folds) -> list[dict]:
    """Treina e avalia o modelo em cada fold (limiares e rótulos do próprio fold)."""
    X = train_df[feature_columns()]
    resultados = []
    for i, f in enumerate(folds, 1):
        model = build_model(name)
        model.fit(X.iloc[f.train_idx], f.y_train)
        pred = model.predict(X.iloc[f.valid_idx])
        m = compute_metrics(f.y_valid, pred)
        resultados.append({"fold": i, **{k: v for k, v in m.items() if k != "confusion_matrix"}})
    return resultados


def cv_persistence(train_df: pd.DataFrame, folds) -> list[dict]:
    resultados = []
    for i, f in enumerate(folds, 1):
        m = persistence_baseline(train_df.iloc[f.valid_idx], f.thresholds)
        resultados.append({"fold": i, **{k: v for k, v in m.items() if k != "confusion_matrix"}})
    return resultados


def mean_folds(resultados: list[dict], chave: str) -> float:
    return float(np.mean([r[chave] for r in resultados if r["fold"] in FOLDS_NA_MEDIA]))


def flat(prefixo: str, m: dict) -> dict:
    return {f"{prefixo}_{k}": v for k, v in m.items() if k != "confusion_matrix"}


@dataclass
class ModelResult:
    name: str
    row: dict
    cv: list[dict]
    metrics: dict
    figures: list[Path]
    fitted: object = None


def evaluate_candidate(name: str, split: LockedSplit, folds, figures_dir: Path) -> ModelResult:
    thr = split.thresholds
    X_tr, X_va = split.train[feature_columns()], split.val[feature_columns()]
    y_tr = apply_thresholds(split.train["target_casos"], thr)
    y_va = apply_thresholds(split.val["target_casos"], thr)

    inicio = time.perf_counter()
    cv = cv_scores(name, split.train, folds)
    cv_segundos = time.perf_counter() - inicio

    model = build_model(name)
    inicio = time.perf_counter()
    model.fit(X_tr, y_tr)
    fit_segundos = time.perf_counter() - inicio

    m_train = compute_metrics(y_tr, model.predict(X_tr))
    proba_va = predict_proba_full(model, X_va)
    m_val = compute_metrics(y_va, model.predict(X_va))
    roc = roc_data(y_va, proba_va)

    figures_dir.mkdir(parents=True, exist_ok=True)
    f_cm = figures_dir / f"cm_{name}.png"
    f_roc = figures_dir / f"roc_{name}.png"
    plot_confusion(m_val["confusion_matrix"], f"{DISPLAY_NAMES[name]} — validação", f_cm)
    plot_roc(roc, f"{DISPLAY_NAMES[name]} — validação", f_roc)

    cv_f1 = mean_folds(cv, "f1_macro")
    row = {
        "modelo": DISPLAY_NAMES[name],
        "f1_macro_cv_f2_5": cv_f1,
        "f1_macro_cv_f1": cv[0]["f1_macro"],
        "recall_alto_cv_f2_5": mean_folds(cv, "recall_alto"),
        "f1_macro_treino": m_train["f1_macro"],
        "f1_macro_val": m_val["f1_macro"],
        "balanced_accuracy_val": m_val["balanced_accuracy"],
        "recall_alto_val": m_val["recall_alto"],
        "auc_macro_val": roc["auc_macro"],
        "gap_treino_val": m_train["f1_macro"] - m_val["f1_macro"],
        "gap_treino_cv": m_train["f1_macro"] - cv_f1,
        "fit_segundos": fit_segundos,
        "cv_segundos": cv_segundos,
    }
    metrics = {
        **{f"cv_f1_macro_fold{r['fold']}": r["f1_macro"] for r in cv},
        "cv_f1_macro_mean_f2_5": cv_f1,
        "cv_recall_alto_mean_f2_5": row["recall_alto_cv_f2_5"],
        **flat("train", m_train),
        **flat("val", m_val),
        "val_auc_macro": roc["auc_macro"],
        "gap_treino_val": row["gap_treino_val"],
        "gap_treino_cv": row["gap_treino_cv"],
        "fit_segundos": fit_segundos,
        "cv_segundos": cv_segundos,
    }
    metrics["_confusion_matrix_val"] = m_val["confusion_matrix"]
    return ModelResult(name, row, cv, metrics, [f_cm, f_roc], model)


def evaluate_persistence(split: LockedSplit, folds) -> ModelResult:
    thr = split.thresholds
    cv = cv_persistence(split.train, folds)
    m_train = persistence_baseline(split.train, thr)
    m_val = persistence_baseline(split.val, thr)
    cv_f1 = mean_folds(cv, "f1_macro")
    row = {
        "modelo": "Persistência",
        "f1_macro_cv_f2_5": cv_f1,
        "f1_macro_cv_f1": cv[0]["f1_macro"],
        "recall_alto_cv_f2_5": mean_folds(cv, "recall_alto"),
        "f1_macro_treino": m_train["f1_macro"],
        "f1_macro_val": m_val["f1_macro"],
        "balanced_accuracy_val": m_val["balanced_accuracy"],
        "recall_alto_val": m_val["recall_alto"],
        "auc_macro_val": float("nan"),
        "gap_treino_val": m_train["f1_macro"] - m_val["f1_macro"],
        "gap_treino_cv": m_train["f1_macro"] - cv_f1,
        "fit_segundos": 0.0,
        "cv_segundos": 0.0,
    }
    metrics = {
        **{f"cv_f1_macro_fold{r['fold']}": r["f1_macro"] for r in cv},
        "cv_f1_macro_mean_f2_5": cv_f1,
        "cv_recall_alto_mean_f2_5": row["recall_alto_cv_f2_5"],
        **flat("train", m_train),
        **flat("val", m_val),
        "gap_treino_val": row["gap_treino_val"],
        "gap_treino_cv": row["gap_treino_cv"],
    }
    metrics["_confusion_matrix_val"] = m_val["confusion_matrix"]
    return ModelResult(PERSISTENCE, row, cv, metrics, [])


def model_params(name: str, model, split: LockedSplit) -> dict:
    clf = model.named_steps["clf"]
    simples = {f"clf__{k}": v for k, v in clf.get_params().items() if isinstance(v, (str, int, float, bool, tuple, type(None)))}
    return {
        "modelo": DISPLAY_NAMES[name],
        "imputer": "SimpleImputer(median)",
        "scaler": "StandardScaler" if name in NEEDS_SCALER else "nenhum",
        "class_weight_suporte": CLASS_WEIGHT_SUPPORT[name],
        "seed": config.SEED,
        "limiar_q_mid": split.thresholds[0],
        "limiar_q_high": split.thresholds[1],
        "n_features": len(feature_columns()),
        "n_treino": len(split.train),
        "n_validacao": len(split.val),
        "cv_splits": config.CV_SPLITS,
        "cv_folds_na_media": "2-5",
        **simples,
    }


def log_result(tracker: Tracker, res: ModelResult, params: dict, extra_artifacts: list[Path] | None = None) -> None:
    metrics = {k: v for k, v in res.metrics.items() if not k.startswith("_") and not pd.isna(v)}
    tracker.log_params(params)
    tracker.log_metrics(metrics)
    tracker.log_dict({"confusion_matrix_val": res.metrics["_confusion_matrix_val"], "classes": config.CLASSES},
                     "confusion_matrix_val.json")
    tracker.log_dict({"cv_folds": res.cv}, "cv_folds.json")
    for p in [*res.figures, *(extra_artifacts or [])]:
        tracker.log_artifact(p)


def rf_importance(model, figures_dir: Path, reports_dir: Path) -> tuple[pd.DataFrame, list[Path]]:
    imp = pd.DataFrame({"feature": feature_columns(), "importancia": model.named_steps["clf"].feature_importances_})
    imp = imp.sort_values("importancia", ascending=False)
    csv = reports_dir / "importancia_rf.csv"
    png = figures_dir / "importancia_rf.png"
    imp.to_csv(csv, index=False)
    plot_importance(imp, png)
    return imp, [csv, png]


def run_experiment(models: list[str], experiment: str, df: pd.DataFrame, tracker: Tracker,
                   reports_dir: Path, figures_dir: Path, csv_name: str, comparison: bool) -> pd.DataFrame:
    """Treina cada modelo no treino, avalia na validação e na CV, e grava métricas e figuras.

    df: saída de build_features. O teste fica bloqueado durante todo o experimento.
    """
    split = locked_split(df)
    folds = expanding_window_splits(split.train)
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    resultados = []
    persist = evaluate_persistence(split, folds)
    with tracker.run(PERSISTENCE, {"tipo": "referencia", "experimento": experiment}):
        log_result(tracker, persist, {"modelo": "Persistência", "seed": config.SEED,
                                      "limiar_q_mid": split.thresholds[0], "limiar_q_high": split.thresholds[1],
                                      "n_treino": len(split.train), "n_validacao": len(split.val)})
    resultados.append(persist)

    importancia = None
    for name in models:
        res = evaluate_candidate(name, split, folds, figures_dir)
        extras = []
        if comparison and name == "rf":
            importancia, extras = rf_importance(res.fitted, figures_dir, reports_dir)
        with tracker.run(DISPLAY_NAMES[name], {"tipo": "modelo", "experimento": experiment}):
            log_result(tracker, res, model_params(name, res.fitted, split), extras)
        resultados.append(res)
        lento = " (LENTO)" if res.row["fit_segundos"] + res.row["cv_segundos"] > MODELO_LENTO_SEGUNDOS else ""
        print(f"{DISPLAY_NAMES[name]:<20} cv f2-5={res.row['f1_macro_cv_f2_5']:.3f}  val={res.row['f1_macro_val']:.3f}  "
              f"recall_alto_val={res.row['recall_alto_val']:.3f}  tempo={res.row['fit_segundos'] + res.row['cv_segundos']:.0f}s{lento}")

    tabela = pd.DataFrame([r.row for r in resultados])
    tabela.to_csv(reports_dir / csv_name, index=False)
    if comparison:
        grouped_bars(tabela, {"f1_macro_cv_f2_5": "CV (folds 2–5)", "f1_macro_val": "validação"},
                     "F1-macro por modelo", figures_dir / "f1_macro_comparacao.png", "F1-macro")
        grouped_bars(tabela, {"recall_alto_cv_f2_5": "CV (folds 2–5)", "recall_alto_val": "validação"},
                     "Recall da classe alto por modelo", figures_dir / "recall_alto_comparacao.png", "recall alto")
        grouped_bars(tabela, {"f1_macro_treino": "treino", "f1_macro_cv_f2_5": "CV (folds 2–5)",
                              "f1_macro_val": "validação"},
                     "F1-macro: treino x CV x validação (gap = overfitting)", figures_dir / "gap_overfitting.png",
                     "F1-macro")
    return tabela


def main(argv=None) -> pd.DataFrame:
    parser = argparse.ArgumentParser(description="Experimentos 01 e 02 do AnteceDengue")
    parser.add_argument("--exp", choices=["01", "02"], required=True)
    parser.add_argument("--no-mlflow", action="store_true", help="não registra nada no MLflow")
    args = parser.parse_args(argv)

    panel, clima = load_inputs()
    df = build_features(panel, clima)
    comparison = args.exp == "02"
    experiment = config.EXP_COMPARE if comparison else config.EXP_BASELINE
    models = candidate_names() if comparison else ["logreg"]
    csv_name = "metricas_comparacao.csv" if comparison else "metricas_baseline.csv"
    tracker = Tracker(experiment, enabled=not args.no_mlflow)
    tabela = run_experiment(models, experiment, df, tracker, config.REPORTS_DIR, FIGURES_DIR, csv_name, comparison)
    print(tabela.round(3).to_string(index=False))
    return tabela


if __name__ == "__main__":
    main()
