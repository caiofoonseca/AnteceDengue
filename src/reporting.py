"""Gráficos e utilitários de avaliação compartilhados pelos experimentos."""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import auc, roc_curve

from src import config

AZUL, LARANJA, CINZA, VERDE = "#2b6cb0", "#c2410c", "#6b7280", "#2f855a"
FOLDS_NA_MEDIA = (2, 3, 4, 5)


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


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    linhas = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        linhas.append("| " + " | ".join(str(x).replace("|", "\|") for x in row) + " |")
    return "\n".join(linhas)


def plot_learning_curve(tabela: pd.DataFrame, titulo: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.plot(tabela["linhas_treino"], tabela["f1_macro_treino"], color=AZUL, lw=2, marker="o", label="treino")
    ax.plot(tabela["linhas_treino"], tabela["f1_macro_val"], color=LARANJA, lw=2, ls="--", marker="s",
            label="validação")
    ax.set_xlabel("linhas de treino (semanas mais antigas primeiro)")
    ax.set_ylabel("F1-macro")
    ax.set_title(titulo, fontsize=10, loc="left")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e7eb", lw=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
