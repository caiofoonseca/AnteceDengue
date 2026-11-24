import datetime as dt
import json

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.pool import StaticPool

from api.main import create_app
from api.model_store import LoadedModel, ModelLoadError, load_champion
from api.repository import Repository
from src import config
from src.db import init_db, sensor_weekly
from src.features import build_features, feature_columns
from src.labels import apply_thresholds
from src.models import build_model
from tests.conftest import make_clima, make_panel

BAIRROS = ("BOA VIAGEM", "VARZEA", "COHAB")


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory):
    base = tmp_path_factory.mktemp("api")
    panel = make_panel(n_weeks=40, bairros=BAIRROS)
    panel.to_csv(base / "panel.csv", index=False)
    df = build_features(panel, make_clima(40), city=True)
    features = feature_columns(True)
    y = apply_thresholds(df["target_casos"], (1.0, 4.0))
    modelo = build_model("rf", {"clf__n_estimators": 20}).fit(df[features], y)
    meta = {"sklearn_version": __import__("sklearn").__version__, "model_name": "RandomForest", "best_params": {},
            "thresholds": [1.0, 4.0], "classes": config.CLASSES, "features": features,
            "train_period": {"inicio": "2020-01-01", "fim": "2020-09-01"},
            "validation_metrics": {"f1_macro": 0.6}, "test_metrics": {"f1_macro": 0.61}, "mlflow_run_id": "abc",
            "trained_at": "2026-11-23T00:00:00+00:00"}
    semana = panel["week_start"].max()
    pd.DataFrame({
        "bairro": list(BAIRROS), "week_start": semana, "target_week": semana + pd.Timedelta(weeks=1),
        "classe_prevista": [2, 1, 0], "rotulo_previsto": ["alto", "medio", "baixo"],
        "prob_baixo": [0.1, 0.3, 0.8], "prob_medio": [0.1, 0.5, 0.15], "prob_alto": [0.8, 0.2, 0.05],
        "risk_score": [85.0, 35.0, 12.5], "rank": [1, 2, 3]}).to_csv(base / "pred.csv", index=False)
    return base, LoadedModel(modelo, meta, "arquivo de teste", None, None), meta


def make_repo(base, com_predicoes=True, com_sensor=True):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    init_db(engine)
    if com_sensor:
        with engine.begin() as conn:
            conn.execute(insert(sensor_weekly), [
                {"bairro": "BOA VIAGEM", "week_start": dt.date(2025, 2, 23), "temp_media": 27.0, "umid_media": 70.0,
                 "chuva_mm": 3.5, "n_leituras": 2, "bateria_min": 3.9},
                {"bairro": "BOA VIAGEM", "week_start": dt.date(2025, 3, 2), "temp_media": 28.0, "umid_media": 72.0,
                 "chuva_mm": 4.0, "n_leituras": 1, "bateria_min": 3.7},
                {"bairro": "VARZEA", "week_start": dt.date(2025, 3, 2), "temp_media": 26.0, "umid_media": 80.0,
                 "chuva_mm": 0.0, "n_leituras": 5, "bateria_min": 3.5}])
    pred = base / "pred.csv" if com_predicoes else base / "nao_existe.csv"
    return Repository(panel_path=base / "panel.csv", predictions_path=pred, engine=engine)


@pytest.fixture
def client(ambiente):
    base, loaded, _ = ambiente
    with TestClient(create_app(loaded, make_repo(base))) as c:
        yield c


def test_health(client):
    r = client.get("/health").json()
    assert r == {"status": "ok", "model_loaded": True, "model_source": "arquivo de teste", "sensor_db": True,
                 "predictions_file": True}


def test_health_degradado_sem_predicoes(ambiente):
    base, loaded, _ = ambiente
    with TestClient(create_app(loaded, make_repo(base, com_predicoes=False))) as c:
        r = c.get("/health").json()
    assert r["status"] == "degradado" and r["predictions_file"] is False and r["model_loaded"] is True


def test_model(client, ambiente):
    r = client.get("/model").json()
    assert r["name"] == "RandomForest" and r["features"] == ambiente[2]["features"]
    assert r["thresholds"] == [1.0, 4.0] and r["classes"] == config.CLASSES
    assert r["validation_metrics"]["f1_macro"] == 0.6 and r["test_metrics"]["f1_macro"] == 0.61
    assert r["train_period"]["inicio"] == "2020-01-01" and r["sklearn_version_api"]


def test_predictions_latest(client):
    r = client.get("/predictions/latest")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == 3 and [p["rank"] for p in corpo["predictions"]] == [1, 2, 3]
    assert corpo["predictions"][0]["bairro"] == "BOA VIAGEM" and "risk_score" in corpo["predictions"][0]
    assert corpo["target_week"] > corpo["week_start"]


def test_predictions_filtro_top_e_classe(client):
    top2 = client.get("/predictions/latest?top=2").json()["predictions"]
    assert [p["bairro"] for p in top2] == ["BOA VIAGEM", "VARZEA"]
    so_medio = client.get("/predictions/latest?classe=medio").json()
    assert so_medio["total"] == 1 and so_medio["predictions"][0]["rotulo_previsto"] == "medio"
    assert client.get("/predictions/latest?classe=alto&top=5").json()["total"] == 1
    assert client.get("/predictions/latest?classe=critico").status_code == 422
    assert client.get("/predictions/latest?top=0").status_code == 422


def test_predictions_arquivo_ausente_da_503(ambiente):
    base, loaded, _ = ambiente
    with TestClient(create_app(loaded, make_repo(base, com_predicoes=False))) as c:
        r = c.get("/predictions/latest")
        assert r.status_code == 503 and "predict_batch" in r.json()["detail"]
        detalhe = c.get("/bairros/VARZEA")
        assert detalhe.status_code == 200 and detalhe.json()["previsao"] is None
        assert "Sem previsão" in detalhe.json()["nota"]


def test_bairros(client):
    r = client.get("/bairros").json()
    assert r["total"] == 3 and r["bairros"] == sorted(BAIRROS)


def test_bairro_detalhe(client):
    r = client.get("/bairros/BOA%20VIAGEM").json()
    assert r["bairro"] == "BOA VIAGEM" and r["previsao"]["rank"] == 1
    assert len(r["casos_semanais"]) == 26
    semanas = [c["week_start"] for c in r["casos_semanais"]]
    assert semanas == sorted(semanas)
    assert [s["chuva_mm"] for s in r["sensor_semanal"]] == [3.5, 4.0]


@pytest.mark.parametrize("nome", ["boa viagem", "Boa%20Viagem", "BOA%20VIAGEM"])
def test_bairro_sem_diferenca_de_caixa(client, nome):
    assert client.get(f"/bairros/{nome}").json()["bairro"] == "BOA VIAGEM"


def test_bairro_sem_acento(client):
    assert client.get("/bairros/v%C3%A1rzea").json()["bairro"] == "VARZEA"
    assert client.get("/bairros/V%C3%81RZEA").json()["bairro"] == "VARZEA"


def test_bairro_inexistente_da_404_com_sugestao(client):
    r = client.get("/bairros/BOA%20VIAJEM")
    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"] and "BOA VIAGEM" in r.json()["detail"]
    assert client.get("/bairros/ATLANTIDA").status_code == 404


def exemplo(meta):
    return {f: 1.0 for f in meta["features"]}


def test_predict_probabilidades_somam_um(client, ambiente):
    meta = ambiente[2]
    linhas = [exemplo(meta), {**exemplo(meta), "casos_t": 40, "casos_mm4": 30.0, "extra": "ignorada"}]
    r = client.post("/predict", json={"rows": linhas})
    assert r.status_code == 200
    previsoes = r.json()["predictions"]
    assert len(previsoes) == 2
    for p in previsoes:
        assert p["prob_baixo"] + p["prob_medio"] + p["prob_alto"] == pytest.approx(1.0)
        assert p["classe_prevista"] in (0, 1, 2) and p["rotulo_previsto"] == config.CLASSES[p["classe_prevista"]]
        assert 0 <= p["risk_score"] <= 100


def test_predict_feature_faltando_da_422_listando(client, ambiente):
    meta = ambiente[2]
    linha = exemplo(meta)
    del linha["casos_mm4"], linha["sazon_sin"]
    r = client.post("/predict", json={"rows": [exemplo(meta), linha]})
    assert r.status_code == 422
    detalhe = r.json()["detail"]
    assert {(d["linha"], d["feature"], d["problema"]) for d in detalhe} == {
        (1, "casos_mm4", "ausente"), (1, "sazon_sin", "ausente")}


def test_predict_valor_invalido_da_422(client, ambiente):
    meta = ambiente[2]
    linha = {**exemplo(meta), "casos_t": "muitos", "casos_lag1": None, "casos_lag2": True}
    r = client.post("/predict", json={"rows": [linha]})
    assert r.status_code == 422
    assert {d["feature"] for d in r.json()["detail"]} == {"casos_t", "casos_lag1", "casos_lag2"}
    assert client.post("/predict", json={"rows": []}).status_code == 422
    assert client.post("/predict", json={}).status_code == 422


def test_sensor_weekly_e_filtros(client):
    todos = client.get("/sensor/weekly").json()
    assert todos["total"] == 3 and "não entram na previsão" in todos["nota"]
    assert client.get("/sensor/weekly?bairro=boa viagem").json()["total"] == 2
    desde = client.get("/sensor/weekly?desde=2025-03-01").json()
    assert desde["total"] == 2 and all(i["week_start"] >= "2025-03-01" for i in desde["items"])
    assert client.get("/sensor/weekly?bairro=varzea&desde=2025-03-02").json()["total"] == 1
    assert client.get("/sensor/weekly?bairro=nada").status_code == 404
    assert client.get("/sensor/weekly?desde=ontem").status_code == 422


def test_sensor_fora_do_ar(ambiente):
    base, loaded, _ = ambiente
    repo = Repository(panel_path=base / "panel.csv", predictions_path=base / "pred.csv",
                      database_url="postgresql://x:y@127.0.0.1:1/nada")
    with TestClient(create_app(loaded, repo)) as c:
        assert c.get("/health").json()["sensor_db"] is False
        assert c.get("/sensor/weekly").status_code == 503
        r = c.get("/bairros/VARZEA")
        assert r.status_code == 200 and r.json()["sensor_semanal"] == []
        assert "Banco do sensor indisponível" in r.json()["nota"]


def test_cors_configuravel(ambiente):
    base, loaded, _ = ambiente
    app = create_app(loaded, make_repo(base), cors_origins=["http://dash.local"])
    with TestClient(app) as c:
        r = c.get("/health", headers={"Origin": "http://dash.local"})
        assert r.headers["access-control-allow-origin"] == "http://dash.local"
        r = c.get("/health", headers={"Origin": "http://outro.com"})
        assert "access-control-allow-origin" not in r.headers


def test_api_nao_sobe_sem_modelo(tmp_path):
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({"sklearn_version": "0"}), encoding="utf-8")
    with pytest.raises(ModelLoadError, match="Não foi possível carregar o modelo"):
        load_champion(tmp_path / "nao_existe.joblib", meta, use_registry=False)
    with pytest.raises(ModelLoadError, match="final"):
        load_champion(tmp_path / "x.joblib", tmp_path / "sem_meta.json", use_registry=False)


def test_lifespan_falha_sem_modelo(monkeypatch, ambiente):
    import api.main as principal

    def falha(*args, **kwargs):
        raise ModelLoadError("modelo ausente de propósito")

    monkeypatch.setattr(principal, "load_champion", falha)
    with pytest.raises(ModelLoadError, match="ausente de propósito"):
        with TestClient(principal.create_app(repository=make_repo(ambiente[0]))):
            pass


def test_aviso_de_versao_diferente_do_sklearn(ambiente, tmp_path, caplog):
    base, loaded, meta = ambiente
    joblib.dump(loaded.model, tmp_path / "m.joblib")
    (tmp_path / "meta.json").write_text(json.dumps({**meta, "sklearn_version": "0.0.1"}), encoding="utf-8")
    with caplog.at_level("WARNING", logger="api.model_store"):
        carregado = load_champion(tmp_path / "m.joblib", tmp_path / "meta.json", use_registry=False)
    assert any("difere da versão do treino" in m for m in caplog.messages)
    assert carregado.source.startswith("arquivo")


def test_openapi_lista_endpoints_e_descreve_risk_score(client):
    esquema = client.get("/openapi.json").json()
    assert set(esquema["paths"]) == {"/health", "/model", "/predictions/latest", "/bairros", "/bairros/{bairro}",
                                     "/predict", "/sensor/weekly"}
    campos = esquema["components"]["schemas"]["PredictionItem"]["properties"]
    assert "NÃO é uma probabilidade" in campos["risk_score"]["description"]
    assert "calibrado" in campos["risk_score"]["description"]
    assert not any("surto" in k for k in campos)


def test_url_postgres_usa_psycopg2():
    from src.db import normalize_database_url

    assert normalize_database_url("postgresql://u:p@h:5432/d") == "postgresql+psycopg2://u:p@h:5432/d"
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"
