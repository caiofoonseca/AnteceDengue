"""Modelos Pydantic de resposta e entrada da API."""
import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

RISK_SCORE_DESC = (
    "Índice de ordenação de 0 a 100, calculado como 50*prob_medio + 100*prob_alto. NÃO é uma probabilidade "
    "de surto e NÃO é calibrado: só serve para ordenar bairros entre si."
)


class HealthResponse(BaseModel):
    status: str = Field(description="'ok' se tudo responde; 'degradado' se algo opcional está fora.")
    model_loaded: bool = Field(description="Se o modelo foi carregado na inicialização.")
    model_source: str = Field(description="De onde o modelo foi carregado (Registry ou arquivo).")
    sensor_db: bool = Field(description="Se o banco das leituras do sensor responde.")
    predictions_file: bool = Field(description="Se existe o arquivo de previsões em lote.")
    model_config = {"protected_namespaces": (), "json_schema_extra": {"examples": [{
        "status": "ok", "model_loaded": True, "model_source": "arquivo best_model.joblib", "sensor_db": True,
        "predictions_file": True}]}}


class ModelInfo(BaseModel):
    name: str = Field(description="Tipo do modelo.")
    version: str | None = Field(description="Versão no MLflow Registry (nula se carregado do arquivo).")
    alias: str | None = Field(description="Alias no Registry (champion), se carregado de lá.")
    source: str
    mlflow_run_id: str | None
    sklearn_version_treino: str
    sklearn_version_api: str
    classes: list[str]
    features: list[str] = Field(description="Features exigidas, na ordem do modelo.")
    thresholds: list[float] = Field(description="Limiares de casos/semana entre baixo, médio e alto (do treino).")
    train_period: dict[str, Any]
    best_params: dict[str, Any]
    validation_metrics: dict[str, Any]
    test_metrics: dict[str, Any]
    trained_at: str | None


class PredictionItem(BaseModel):
    bairro: str
    week_start: dt.date = Field(description="Semana t usada como base (domingo).")
    target_week: dt.date = Field(description="Semana prevista (t+1).")
    classe_prevista: int = Field(description="0 = baixo, 1 = médio, 2 = alto.")
    rotulo_previsto: str
    prob_baixo: float
    prob_medio: float
    prob_alto: float
    risk_score: float = Field(description=RISK_SCORE_DESC)
    rank: int = Field(description="1 = maior risk_score.")
    model_config = {"json_schema_extra": {"examples": [{
        "bairro": "BOA VIAGEM", "week_start": "2025-08-17", "target_week": "2025-08-24", "classe_prevista": 2,
        "rotulo_previsto": "alto", "prob_baixo": 0.005, "prob_medio": 0.055, "prob_alto": 0.94,
        "risk_score": 96.8, "rank": 4}]}}


class PredictionsResponse(BaseModel):
    week_start: dt.date | None
    target_week: dt.date | None
    total: int = Field(description="Quantidade de bairros devolvidos depois dos filtros.")
    classe: str | None = Field(description="Filtro de classe aplicado.")
    top: int | None = Field(description="Limite aplicado (os N de maior risk_score).")
    predictions: list[PredictionItem]
    fonte: str | None = Field(None, description="De onde vieram as previsões: postgres (DAG semanal) ou csv (fallback).")


class BairrosResponse(BaseModel):
    total: int
    bairros: list[str]


class CasosSemana(BaseModel):
    week_start: dt.date
    casos: int = Field(description="Casos confirmados na semana (painel do portal; chegam com atraso).")


class SensorSemana(BaseModel):
    bairro: str
    week_start: dt.date = Field(description="Domingo da semana, fuso America/Recife.")
    temp_media: float | None
    umid_media: float | None
    chuva_mm: float | None = Field(description="Chuva total da semana (soma das leituras).")
    n_leituras: int
    bateria_min: float | None


class BairroDetail(BaseModel):
    bairro: str
    previsao: PredictionItem | None
    casos_semanais: list[CasosSemana] = Field(description="Últimas 26 semanas do painel.")
    sensor_semanal: list[SensorSemana] = Field(description="Leituras do sensor: exibidas, mas NÃO entram na previsão.")
    nota: str | None = None


class SensorWeeklyResponse(BaseModel):
    total: int
    items: list[SensorSemana]
    nota: str = "As leituras do sensor são exibidas, mas não entram na previsão do modelo."


class PredictRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=1000,
                                       description="Linhas de features (as mesmas de GET /model); chaves extras são ignoradas.")
    model_config = {"json_schema_extra": {"examples": [{"rows": [{
        "casos_t": 3, "casos_lag1": 2, "casos_lag2": 1, "casos_lag3": 1, "casos_mm4": 1.75, "casos_mm8": 1.2,
        "tendencia": 0.55, "casos_media_hist": 1.9, "temp_media_lag1": 27.1, "temp_media_lag2": 27.0,
        "temp_media_lag4": 26.5, "temp_media_lag8": 27.8, "umid_media_lag1": 74.0, "umid_media_lag2": 73.5,
        "umid_media_lag4": 76.0, "umid_media_lag8": 70.0, "chuva_acum2": 25.0, "chuva_acum4": 40.0,
        "chuva_acum8": 70.0, "sazon_sin": 0.6, "sazon_cos": -0.7, "cidade_total_t": 150, "cidade_lag1": 140,
        "cidade_lag2": 120, "cidade_lag3": 100, "cidade_lag4": 90, "cidade_var_semanal": 10}]}]}}


class PredictRow(BaseModel):
    classe_prevista: int
    rotulo_previsto: str
    prob_baixo: float
    prob_medio: float
    prob_alto: float
    risk_score: float = Field(description=RISK_SCORE_DESC)


class PredictResponse(BaseModel):
    model: str
    predictions: list[PredictRow]
