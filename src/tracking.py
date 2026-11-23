"""Utilitário fino sobre o MLflow. Com enabled=False (flag --no-mlflow) todas as chamadas são no-op."""
from contextlib import contextmanager
from pathlib import Path

import sklearn

from src import config


class Tracker:
    def __init__(self, experiment: str, enabled: bool = True):
        self.experiment = experiment
        self.enabled = enabled
        self._mlflow = None
        if enabled:
            import mlflow

            mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
            mlflow.set_experiment(experiment)
            self._mlflow = mlflow

    @property
    def run_id(self) -> str | None:
        if not self.enabled:
            return None
        ativo = self._mlflow.active_run()
        return ativo.info.run_id if ativo else None

    @contextmanager
    def run(self, name: str, tags: dict | None = None, nested: bool = False):
        if not self.enabled:
            yield self
            return
        with self._mlflow.start_run(run_name=name, nested=nested):
            self._mlflow.set_tags({"sklearn_version": sklearn.__version__, **(tags or {})})
            self._mlflow.log_param("sklearn_version", sklearn.__version__)
            yield self

    def log_params(self, params: dict) -> None:
        if self.enabled:
            self._mlflow.log_params({k: str(v)[:500] for k, v in params.items()})

    def log_metrics(self, metrics: dict, step: int | None = None) -> None:
        if self.enabled:
            self._mlflow.log_metrics({k: float(v) for k, v in metrics.items()}, step=step)

    def log_artifact(self, path: Path, artifact_path: str | None = None) -> None:
        if self.enabled:
            self._mlflow.log_artifact(str(path), artifact_path)

    def log_dict(self, data: dict, filename: str) -> None:
        if self.enabled:
            self._mlflow.log_dict(data, filename)

    def log_model(self, pipeline, input_example, registered_name: str) -> str | None:
        """Registra o Pipeline no run ativo e no Model Registry; devolve a versão criada."""
        if not self.enabled:
            return None
        import mlflow.sklearn

        info = mlflow.sklearn.log_model(pipeline, name="model", input_example=input_example,
                                        registered_model_name=registered_name,
                                        serialization_format="cloudpickle")
        return str(info.registered_model_version)

    def set_alias(self, registered_name: str, alias: str, version: str) -> None:
        if self.enabled:
            from mlflow.tracking import MlflowClient

            MlflowClient().set_registered_model_alias(registered_name, alias, version)
