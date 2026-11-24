"""Configuração central do AnteceDengue (constantes e caminhos)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"

SEED = 42

CASE_CODES = (1, 2, 3, 4, 10, 11, 12)
PANEL_START_YEAR = 2015
PANEL_END_YEAR = 2025
PANEL_END = "2025-08-17"
BAIRRO_FUZZY_CUTOFF = 0.90

CLASSES = ["baixo", "medio", "alto"]
Q_MID = 0.60
Q_HIGH = 0.85

CASE_LAGS = (1, 2, 3)
ROLLING_WINDOWS = (4, 8)
CLIMATE_LAGS = (1, 2, 4, 8)
RAIN_WINDOWS = (2, 4, 8)
CLIMATE_FFILL_LIMIT = 2
MAX_HISTORY_WEEKS = 8
CITY_LAGS = (1, 2, 3, 4)

TEST_WEEKS = 26
VAL_WEEKS = 26
GAP_WEEKS = 1
CV_SPLITS = 5

SEARCH_N_ITER = 30
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_BLOCK_WEEKS = 4
CHAMPION_ALIAS = "champion"
MODEL_PATH = MODELS_DIR / "best_model.joblib"
MODEL_META_PATH = MODELS_DIR / "model_meta.json"
CHOICE_PATH = REPORTS_DIR / "modelo_escolhido.json"
FINAL_TEST_PATH = REPORTS_DIR / "teste_final.json"

EXP_BASELINE = "01-baseline"
EXP_COMPARE = "02-comparacao-modelos"
EXP_TUNING = "03-otimizacao-hiperparametros"
MLFLOW_MODEL_NAME = "antecedengue-risk-classifier"

MQTT_TOPIC = "antecedengue/estacoes/+/leituras"
MQTT_TOPIC_PATTERN = r"^antecedengue/estacoes/([^/]+)/leituras$"
STATIONS_PATH = ROOT / "config" / "stations_bairros.json"
SENSOR_TIMEZONE = "America/Recife"
TEMP_RANGE = (-10.0, 60.0)
HUMIDITY_RANGE = (0.0, 100.0)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://antecedengue:antecedengue@localhost:5432/antecedengue"
)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
