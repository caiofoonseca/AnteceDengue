"""Configuração central do AnteceDengue (constantes e caminhos)."""
import os
from pathlib import Path

# Caminhos (relativos à raiz do repositório)
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"

SEED = 42

# Rótulos de risco
CLASSES = ["baixo", "medio", "alto"]
Q_MID = 0.60
Q_HIGH = 0.85

# Validação temporal
TEST_WEEKS = 26
VAL_WEEKS = 26
GAP_WEEKS = 1
CV_SPLITS = 5

# MLflow
EXP_BASELINE = "01-baseline"
EXP_COMPARE = "02-comparacao-modelos"
EXP_TUNING = "03-otimizacao-hiperparametros"
MLFLOW_MODEL_NAME = "antecedengue-risk-classifier"

# MQTT
MQTT_TOPIC = "antecedengue/estacoes/+/leituras"

# Dependem do ambiente (padrão para desenvolvimento local)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://antecedengue:antecedengue@localhost:5432/antecedengue"
)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
