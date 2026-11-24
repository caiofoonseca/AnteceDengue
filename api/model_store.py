"""Carregamento do modelo champion (MLflow Registry, com fallback para models/best_model.joblib)."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import sklearn

from src import config

log = logging.getLogger("api.model_store")


class ModelLoadError(RuntimeError):
    pass


@dataclass
class LoadedModel:
    model: object
    meta: dict
    source: str
    version: str | None
    alias: str | None

    def predict_proba(self, X) -> np.ndarray:
        """Probabilidades (n, 3) na ordem baixo, medio, alto, mesmo que o treino não tenha visto uma classe."""
        proba = self.model.predict_proba(X)
        completo = np.zeros((len(X), len(config.CLASSES)))
        completo[:, self.model.named_steps["clf"].classes_.astype(int)] = proba
        return completo


def load_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        raise ModelLoadError(f"{meta_path.name} não existe: rode `python -m src.train --final` antes de subir a API.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def load_champion(model_path: Path = config.MODEL_PATH, meta_path: Path = config.MODEL_META_PATH,
                  use_registry: bool = True) -> LoadedModel:
    """Carrega o champion do Registry; se falhar, o joblib local; se nenhum funcionar, levanta ModelLoadError."""
    meta = load_meta(meta_path)
    if meta["sklearn_version"] != sklearn.__version__:
        log.warning("scikit-learn %s difere da versão do treino (%s): previsões podem mudar ou o modelo pode "
                    "não carregar", sklearn.__version__, meta["sklearn_version"])
    motivos = []
    if use_registry:
        try:
            import mlflow
            import mlflow.sklearn
            from mlflow.tracking import MlflowClient

            mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
            uri = f"models:/{config.MLFLOW_MODEL_NAME}@{config.CHAMPION_ALIAS}"
            modelo = mlflow.sklearn.load_model(uri)
            versao = MlflowClient().get_model_version_by_alias(config.MLFLOW_MODEL_NAME, config.CHAMPION_ALIAS)
            log.info("modelo carregado do Registry: %s v%s", config.MLFLOW_MODEL_NAME, versao.version)
            return LoadedModel(modelo, meta, f"MLflow Registry ({uri})", str(versao.version), config.CHAMPION_ALIAS)
        except Exception as erro:
            motivos.append(f"Registry: {type(erro).__name__}: {erro}")
            log.warning("Registry indisponível (%s); tentando %s", type(erro).__name__, model_path.name)
    try:
        modelo = joblib.load(model_path)
        return LoadedModel(modelo, meta, f"arquivo {model_path.name}", None, None)
    except Exception as erro:
        motivos.append(f"joblib ({model_path.name}): {type(erro).__name__}: {erro}")
    raise ModelLoadError("Não foi possível carregar o modelo. " + " | ".join(motivos))
