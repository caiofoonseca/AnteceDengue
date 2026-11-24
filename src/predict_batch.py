"""Inferência em lote: prevê a classe de risco da semana seguinte (t+1) para todos os bairros.

Usa o modelo marcado como champion no MLflow Model Registry; se o Registry não estiver acessível,
usa models/best_model.joblib. As features vêm da ÚLTIMA semana presente no painel (hoje PANEL_END) e
as colunas usadas são exatamente as de models/model_meta.json, na mesma ordem.

Limitações de uso: a previsão cobre a semana seguinte à última semana dos dados; os casos vêm de CSVs
anuais do portal, que chegam com atraso; as leituras do sensor NÃO alimentam o modelo.

risk_score = 50 * prob_medio + 100 * prob_alto é um índice de 0 a 100 para ordenar bairros.
NÃO é uma probabilidade (nem uma taxa de casos): só faz sentido comparar bairros entre si.
"""
import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from src import config
from src.features import build_features, load_inputs
from src.reporting import predict_proba_full

OUTPUT_PATH = config.DATA_PROCESSED / "predictions_latest.csv"
OUTPUT_COLUMNS = ["bairro", "week_start", "target_week", "classe_prevista", "rotulo_previsto", "prob_baixo",
                  "prob_medio", "prob_alto", "risk_score", "rank"]


class FeatureMismatch(ValueError):
    pass


def load_meta(meta_path: Path = config.MODEL_META_PATH) -> dict:
    if not meta_path.exists():
        raise FileNotFoundError(f"{meta_path.name} não existe: rode `python -m src.train --final` antes.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def check_sklearn_version(meta: dict) -> bool:
    """Avisa (sem interromper) se a versão do scikit-learn difere da usada no treino."""
    if meta["sklearn_version"] != sklearn.__version__:
        warnings.warn(
            f"scikit-learn {sklearn.__version__} difere da versão do treino ({meta['sklearn_version']}): "
            "as previsões podem mudar ou o modelo pode não carregar.", RuntimeWarning, stacklevel=2)
        return False
    return True


def load_model(model_path: Path = config.MODEL_PATH, use_registry: bool = True) -> tuple[object, str]:
    """Carrega o champion do Registry; se falhar, o joblib local. Devolve (modelo, origem)."""
    if use_registry:
        try:
            import mlflow
            import mlflow.sklearn

            mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
            uri = f"models:/{config.MLFLOW_MODEL_NAME}@{config.CHAMPION_ALIAS}"
            return mlflow.sklearn.load_model(uri), f"MLflow Registry ({uri})"
        except Exception as erro:
            print(f"Registry indisponível ({type(erro).__name__}); usando {model_path.name}.")
    return joblib.load(model_path), f"arquivo {model_path.name}"


def select_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    faltando = [f for f in features if f not in df.columns]
    if faltando:
        raise FeatureMismatch(f"faltam features exigidas pelo modelo: {faltando}")
    return df[features]


def latest_features(panel: pd.DataFrame, clima: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Linhas (uma por bairro) da última semana do painel, com as features do modelo."""
    city = any(f.startswith("cidade_") for f in features)
    df = build_features(panel, clima, keep_last=True, city=city)
    ultima = df["week_start"].max()
    return df[df["week_start"] == ultima].reset_index(drop=True)


def predict_latest(model, meta: dict, panel: pd.DataFrame, clima: pd.DataFrame) -> pd.DataFrame:
    features = meta["features"]
    base = latest_features(panel, clima, features)
    X = select_features(base, features)
    proba = predict_proba_full(model, X)
    classe = proba.argmax(axis=1)
    out = pd.DataFrame({
        "bairro": base["bairro"],
        "week_start": base["week_start"],
        "target_week": base["week_start"] + pd.Timedelta(weeks=1),
        "classe_prevista": classe,
        "rotulo_previsto": [config.CLASSES[c] for c in classe],
        "prob_baixo": proba[:, 0],
        "prob_medio": proba[:, 1],
        "prob_alto": proba[:, 2],
    })
    out["risk_score"] = 50 * out["prob_medio"] + 100 * out["prob_alto"]
    ordem = out.sort_values(["risk_score", "prob_alto", "bairro"], ascending=[False, False, True]).index
    out["rank"] = pd.Series(np.arange(1, len(out) + 1), index=ordem)
    return out.sort_values("rank").reset_index(drop=True)[OUTPUT_COLUMNS]


def run(output_path: Path = OUTPUT_PATH, model_path: Path = config.MODEL_PATH, meta_path: Path = config.MODEL_META_PATH,
        use_registry: bool = True) -> pd.DataFrame:
    meta = load_meta(meta_path)
    check_sklearn_version(meta)
    model, origem = load_model(model_path, use_registry)
    panel, clima = load_inputs()
    out = predict_latest(model, meta, panel, clima)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Modelo: {meta['model_name']} (origem: {origem})")
    print(f"Semana base t = {out['week_start'].iloc[0].date()}; previsão para t+1 = {out['target_week'].iloc[0].date()}")
    print(f"{len(out)} bairros gravados em {output_path}")
    return out


def main(argv=None) -> pd.DataFrame:
    parser = argparse.ArgumentParser(description="Inferência em lote do AnteceDengue")
    parser.add_argument("--no-registry", action="store_true", help="usa só models/best_model.joblib")
    args = parser.parse_args(argv)
    return run(use_registry=not args.no_registry)


if __name__ == "__main__":
    main()
