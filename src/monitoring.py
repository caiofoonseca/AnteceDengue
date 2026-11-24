"""Registra no MLflow um run de monitoramento da inferência semanal (task registra_monitoramento do DAG).

O run guarda o número de bairros, a distribuição das classes previstas e a semana base. Não avalia o
modelo: não há alvo da semana prevista ainda, e o conjunto de teste não é tocado.
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

from src import config
from src.tracking import Tracker

log = logging.getLogger("monitoring")
EXPERIMENT = "04-monitoramento-semanal"


def summarize(predictions: pd.DataFrame) -> dict:
    contagem = predictions["rotulo_previsto"].value_counts()
    metricas = {"n_bairros": float(len(predictions)), "risk_score_medio": float(predictions["risk_score"].mean()),
                "risk_score_max": float(predictions["risk_score"].max())}
    for classe in config.CLASSES:
        n = int(contagem.get(classe, 0))
        metricas[f"n_{classe}"] = float(n)
        metricas[f"frac_{classe}"] = n / len(predictions)
    return {"week_start": str(pd.to_datetime(predictions["week_start"].iloc[0]).date()),
            "target_week": str(pd.to_datetime(predictions["target_week"].iloc[0]).date()), "metricas": metricas}


def register(predictions_path: Path = config.PREDICTIONS_PATH) -> dict:
    predictions = pd.read_csv(predictions_path)
    resumo = summarize(predictions)
    tracker = Tracker(EXPERIMENT)
    with tracker.run(f"semana-base-{resumo['week_start']}", {"tipo": "monitoramento"}):
        tracker.log_params({"week_start": resumo["week_start"], "target_week": resumo["target_week"]})
        tracker.log_metrics(resumo["metricas"])
    log.info("monitoramento registrado: %s", resumo)
    return resumo


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description="Registra o monitoramento da inferência semanal no MLflow")
    parser.add_argument("--predictions", type=Path, default=config.PREDICTIONS_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    resumo = register(args.predictions)
    print(f"Semana base {resumo['week_start']} (prevista {resumo['target_week']}): {resumo['metricas']}")
    return resumo


if __name__ == "__main__":
    main()
