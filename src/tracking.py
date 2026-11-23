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

    @contextmanager
    def run(self, name: str, tags: dict | None = None):
        if not self.enabled:
            yield self
            return
        with self._mlflow.start_run(run_name=name):
            self._mlflow.set_tags({"sklearn_version": sklearn.__version__, **(tags or {})})
            self._mlflow.log_param("sklearn_version", sklearn.__version__)
            yield self

    def log_params(self, params: dict) -> None:
        if self.enabled:
            self._mlflow.log_params({k: str(v)[:500] for k, v in params.items()})

    def log_metrics(self, metrics: dict) -> None:
        if self.enabled:
            self._mlflow.log_metrics({k: float(v) for k, v in metrics.items()})

    def log_artifact(self, path: Path, artifact_path: str | None = None) -> None:
        if self.enabled:
            self._mlflow.log_artifact(str(path), artifact_path)

    def log_dict(self, data: dict, filename: str) -> None:
        if self.enabled:
            self._mlflow.log_dict(data, filename)
