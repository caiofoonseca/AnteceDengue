"""API FastAPI do AnteceDengue: serve o modelo champion, as previsões em lote e os dados do sensor.

O campo risk_score é um índice de ordenação de 0 a 100, não calibrado (não é probabilidade de surto).
As leituras do sensor são exibidas, mas não entram na previsão.
"""
import datetime as dt
import logging
import math
from contextlib import asynccontextmanager
from typing import Literal

import pandas as pd
import sklearn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from api.model_store import LoadedModel, ModelLoadError, load_champion
from api.repository import PanelUnavailable, PredictionsUnavailable, Repository, SensorDbUnavailable
from api.schemas import (BairroDetail, BairrosResponse, HealthResponse, ModelInfo, PredictionItem,
                         PredictionsResponse, PredictRequest, PredictResponse, PredictRow, SensorSemana,
                         SensorWeeklyResponse)
from src import config

log = logging.getLogger("api")

DESCRICAO = (
    "Previsão de risco de dengue por bairro do Recife para a semana seguinte (t+1).\n\n"
    "**Atenção:** `risk_score` é um índice de ordenação de 0 a 100 (50*prob_medio + 100*prob_alto), "
    "**não calibrado**; não é probabilidade de surto. As leituras do sensor são exibidas, mas **não entram na "
    "previsão**. A previsão vale para a semana seguinte à última semana presente nos dados."
)


def create_app(loaded: LoadedModel | None = None, repository: Repository | None = None,
               cors_origins: list[str] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.model = loaded or load_champion()
        except ModelLoadError as erro:
            log.error("API não sobe: %s", erro)
            raise
        app.state.repo = repository or Repository()
        log.info("API pronta: modelo %s (%s)", app.state.model.meta["model_name"], app.state.model.source)
        yield

    app = FastAPI(title="AnteceDengue API", version="1.0.0", description=DESCRICAO, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins or config.API_CORS_ORIGINS, allow_methods=["*"],
                       allow_headers=["*"])

    def repo(request: Request) -> Repository:
        return request.app.state.repo

    def modelo(request: Request) -> LoadedModel:
        return request.app.state.model

    def bairro_ou_404(r: Repository, nome: str) -> str:
        try:
            oficial = r.resolve_bairro(nome)
        except PanelUnavailable as erro:
            raise HTTPException(503, str(erro))
        if oficial is None:
            sugestoes = r.suggest_bairros(nome)
            dica = f" Você quis dizer: {', '.join(sugestoes)}?" if sugestoes else ""
            raise HTTPException(404, f"Bairro '{nome}' não encontrado. Veja a lista em GET /bairros.{dica}")
        return oficial

    @app.get("/health", response_model=HealthResponse, tags=["Estado"], summary="Estado da API")
    def health(request: Request):
        r, m = repo(request), modelo(request)
        sensor_ok = r.sensor_db_ok()
        return HealthResponse(status="ok" if sensor_ok and r.predictions_available() else "degradado",
                              model_loaded=m.model is not None, model_source=m.source, sensor_db=sensor_ok,
                              predictions_file=r.predictions_available())

    @app.get("/model", response_model=ModelInfo, tags=["Modelo"], summary="Metadados do modelo")
    def model_info(request: Request):
        m = modelo(request)
        meta = m.meta
        return ModelInfo(
            name=meta["model_name"], version=m.version, alias=m.alias, source=m.source,
            mlflow_run_id=meta.get("mlflow_run_id"), sklearn_version_treino=meta["sklearn_version"],
            sklearn_version_api=sklearn.__version__, classes=meta["classes"], features=meta["features"],
            thresholds=meta["thresholds"], train_period=meta["train_period"], best_params=meta["best_params"],
            validation_metrics=meta["validation_metrics"], test_metrics=meta["test_metrics"],
            trained_at=meta.get("trained_at"))

    @app.get("/predictions/latest", response_model=PredictionsResponse, tags=["Previsões"],
             summary="Previsões em lote mais recentes",
             description="Previsão da semana seguinte para todos os bairros, ordenada por risco (rank 1 = maior). "
                         "O filtro `classe` é aplicado antes de `top`.",
             responses={503: {"description": "Arquivo de previsões ausente (rode python -m src.predict_batch)."}})
    def predictions_latest(request: Request,
                           top: int | None = Query(None, ge=1, description="Só os N de maior risco."),
                           classe: Literal["baixo", "medio", "alto"] | None = Query(None, description="Filtra pela classe prevista.")):
        try:
            r = repo(request)
            df = r.predictions()
        except PredictionsUnavailable as erro:
            raise HTTPException(503, str(erro))
        if classe is not None:
            df = df[df["rotulo_previsto"] == classe]
        df = df.sort_values("rank")
        if top is not None:
            df = df.head(top)
        itens = [PredictionItem(**linha) for linha in df.to_dict("records")]
        return PredictionsResponse(week_start=itens[0].week_start if itens else None,
                                   target_week=itens[0].target_week if itens else None, total=len(itens),
                                   classe=classe, top=top, predictions=itens, fonte=r.predictions_source)

    @app.get("/bairros", response_model=BairrosResponse, tags=["Bairros"], summary="Lista de bairros")
    def bairros(request: Request):
        try:
            lista = repo(request).bairros()
        except PanelUnavailable as erro:
            raise HTTPException(503, str(erro))
        return BairrosResponse(total=len(lista), bairros=lista)

    @app.get("/bairros/{bairro}", response_model=BairroDetail, tags=["Bairros"], summary="Detalhe de um bairro",
             description="Previsão mais recente, casos das últimas 26 semanas e leituras semanais do sensor "
                         "(exibidas, mas não usadas na previsão). O nome aceita qualquer caixa e sem acentos.",
             responses={404: {"description": "Bairro inexistente."}})
    def bairro_detail(request: Request, bairro: str):
        r = repo(request)
        oficial = bairro_ou_404(r, bairro)
        notas = []
        previsao = r.latest_prediction(oficial)
        if previsao is None:
            notas.append("Sem previsão em lote disponível (rode python -m src.predict_batch).")
        try:
            sensor = r.sensor_weekly(bairro=oficial)
        except SensorDbUnavailable:
            sensor = []
            notas.append("Banco do sensor indisponível: sem leituras do sensor.")
        return BairroDetail(
            bairro=oficial, previsao=PredictionItem(**previsao) if previsao else None,
            casos_semanais=r.weekly_cases(oficial), sensor_semanal=[SensorSemana(**s) for s in sensor],
            nota=" ".join(notas) or None)

    @app.post("/predict", response_model=PredictResponse, tags=["Previsões"], summary="Previsão para linhas de features",
              description="Recebe linhas com as features de GET /model e devolve classe e probabilidades por linha. "
                          "Chaves extras são ignoradas.",
              responses={422: {"description": "Feature faltando ou valor inválido (lista quais)."}})
    def predict(request: Request, corpo: PredictRequest):
        m = modelo(request)
        features = m.meta["features"]
        problemas = []
        valores = []
        for i, linha in enumerate(corpo.rows):
            vetor = []
            for f in features:
                if f not in linha:
                    problemas.append({"linha": i, "feature": f, "problema": "ausente"})
                    continue
                v = linha[f]
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    problemas.append({"linha": i, "feature": f, "problema": f"valor inválido (esperado número): {v!r}"})
                elif not math.isfinite(v):
                    problemas.append({"linha": i, "feature": f, "problema": "valor não finito"})
                vetor.append(v)
            valores.append(vetor)
        if problemas:
            raise HTTPException(422, detail=problemas)
        X = pd.DataFrame(valores, columns=features)
        proba = m.predict_proba(X)
        classe = proba.argmax(axis=1)
        linhas = [PredictRow(classe_prevista=int(c), rotulo_previsto=config.CLASSES[c], prob_baixo=float(p[0]),
                             prob_medio=float(p[1]), prob_alto=float(p[2]),
                             risk_score=float(50 * p[1] + 100 * p[2])) for c, p in zip(classe, proba)]
        return PredictResponse(model=m.meta["model_name"], predictions=linhas)

    @app.get("/sensor/weekly", response_model=SensorWeeklyResponse, tags=["Sensor"],
             summary="Leituras semanais agregadas do sensor",
             description="Média de temperatura e umidade, chuva total, nº de leituras e menor bateria por bairro e "
                         "semana (domingo a sábado, America/Recife). Exibidas, mas não entram na previsão.",
             responses={404: {"description": "Bairro inexistente."}, 503: {"description": "Banco do sensor fora do ar."}})
    def sensor_weekly(request: Request, bairro: str | None = Query(None, description="Filtra por bairro."),
                      desde: dt.date | None = Query(None, description="Semana inicial (inclusive), aaaa-mm-dd.")):
        r = repo(request)
        oficial = bairro_ou_404(r, bairro) if bairro else None
        try:
            itens = r.sensor_weekly(bairro=oficial, desde=desde)
        except SensorDbUnavailable as erro:
            raise HTTPException(503, str(erro))
        return SensorWeeklyResponse(total=len(itens), items=[SensorSemana(**i) for i in itens])

    return app


app = create_app()
