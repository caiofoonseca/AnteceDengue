"""Alimenta o MLflow do docker compose sem reexecutar o teste.

Registra no experimento 03 as métricas já calculadas (reports/metricas_comparacao.csv, linhas do
experimento 03, e models/model_meta.json) e registra models/best_model.joblib como
antecedengue-risk-classifier com o alias champion. O conjunto de teste NÃO é reavaliado: os números do
teste são só copiados de model_meta.json.

Uso (dentro do container): python scripts/seed_mlflow.py
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import pandas as pd

from src import config
from src.predict_batch import latest_features, select_features
from src.tracking import Tracker

log = logging.getLogger("seed_mlflow")

METRIC_COLUMNS = ["f1_macro_cv_f2_5", "f1_macro_cv_f1", "recall_alto_cv_f2_5", "f1_macro_treino", "f1_macro_val",
                  "balanced_accuracy_val", "recall_alto_val", "auc_macro_val", "gap_treino_val", "gap_treino_cv"]


def flat_metrics(prefix: str, valores: dict) -> dict:
    return {f"{prefix}_{k}": float(v) for k, v in valores.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def seed_comparison(tracker: Tracker, metricas_path: Path) -> int:
    tabela = pd.read_csv(metricas_path, dtype={"experimento": str})
    otimizados = tabela[tabela["experimento"] == "03"]
    for _, linha in otimizados.iterrows():
        with tracker.run(str(linha["modelo"]), {"origem": "seed", "tipo": "otimizado"}):
            tracker.log_params({"modelo": linha["modelo"], "fonte": metricas_path.name})
            tracker.log_metrics({c: linha[c] for c in METRIC_COLUMNS if c in linha and pd.notna(linha[c])})
    return len(otimizados)


def seed_champion(tracker: Tracker, meta: dict, model_path: Path) -> str | None:
    model = joblib.load(model_path)
    panel = pd.read_csv(config.PANEL_PATH, parse_dates=["week_start"])
    clima = pd.read_csv(config.DATA_PROCESSED / "clima_semanal.csv", parse_dates=["week_start"])
    exemplo = select_features(latest_features(panel, clima, meta["features"]), meta["features"]).head(5)
    with tracker.run("modelo-final-seed", {"origem": "seed", "tipo": "final"}):
        tracker.log_params({"modelo": meta["model_name"], "melhores_parametros": json.dumps(meta["best_params"]),
                            "limiares": str(meta["thresholds"]), "run_original": meta.get("mlflow_run_id")})
        tracker.log_metrics({**flat_metrics("val", meta["validation_metrics"]),
                             **flat_metrics("teste", {k: v for k, v in meta["test_metrics"].items()
                                                      if k != "f1_diff_ic95"})})
        tracker.log_dict(meta, "model_meta.json")
        version = tracker.log_model(model, exemplo, config.MLFLOW_MODEL_NAME)
        tracker.set_alias(config.MLFLOW_MODEL_NAME, config.CHAMPION_ALIAS, version)
    return version


def champion_exists() -> bool:
    from mlflow.tracking import MlflowClient

    try:
        MlflowClient().get_model_version_by_alias(config.MLFLOW_MODEL_NAME, config.CHAMPION_ALIAS)
        return True
    except Exception:
        return False


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Alimenta o MLflow do compose sem reavaliar o teste")
    parser.add_argument("--force", action="store_true", help="registra de novo mesmo que já exista um champion")
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    meta = json.loads(config.MODEL_META_PATH.read_text(encoding="utf-8"))
    log.info("MLflow em %s", config.MLFLOW_TRACKING_URI)
    tracker = Tracker(config.EXP_TUNING)
    if champion_exists() and not args.force:
        log.info("o alias %s já existe no Registry; nada a fazer (use --force para registrar outra versão)",
                 config.CHAMPION_ALIAS)
        return
    n = seed_comparison(tracker, config.REPORTS_DIR / "metricas_comparacao.csv")
    log.info("%d modelos otimizados registrados no experimento %s", n, config.EXP_TUNING)
    version = seed_champion(tracker, meta, config.MODEL_PATH)
    log.info("%s versão %s com alias %s (teste não reavaliado)", config.MLFLOW_MODEL_NAME, version,
             config.CHAMPION_ALIAS)


if __name__ == "__main__":
    main()
