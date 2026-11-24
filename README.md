# AnteceDengue
Previsão de risco de dengue por bairro do Recife (ML + MLOps) — Projeto G15, CESAR School

## Como rodar localmente

Requer Python 3.11.

```powershell
# 1. criar o ambiente virtual
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

# 2. instalar as dependências
pip install -r requirements.txt

# 3. copiar as variáveis de ambiente (opcional em desenvolvimento)
copy .env.example .env

# 4. rodar os testes
pytest
```

## Experimentos de ML (MLflow)

Pré-requisito: `data/processed/panel.csv` e `data/processed/clima_semanal.csv` (ver `docs/DADOS.md`: `python scripts/build_panel.py` e `python scripts/build_clima.py`).

```powershell
python -m src.train --exp 01                 # 01-baseline: regressão logística + persistência
python -m src.train --exp 02                 # 02-comparacao-modelos: 6 candidatos + persistência
python -m src.train --exp 03                 # 03: ablação, RandomizedSearchCV (RF e LogReg), escolha do modelo
python -m src.train --final                  # reajusta em treino+validação, avalia o teste UMA vez, registra o champion
python -m src.train --exp 02 --no-mlflow     # roda sem registrar no MLflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Saídas: `reports/metricas_comparacao.csv` (experimento 02), `reports/metricas_baseline.csv` (experimento 01), `reports/importancia_rf.csv` e figuras em `reports/figuras/`. Os experimentos treinam no treino e avaliam na validação; o conjunto de teste fica bloqueado em código (`TestSetLocked`).

### Otimização e avaliação final (passo 7)

`--exp 03` grava `reports/modelo_escolhido.json`, `reports/otimizacao_resumo.md` e `reports/busca_*.csv`. `--final` grava `reports/teste_final.json` e `.md`, `models/best_model.joblib`, `models/model_meta.json` e registra o modelo `antecedengue-risk-classifier` com o alias `champion`. Se `teste_final.json` já existir, `--final` se recusa a rodar; `--force-reeval` ignora a trava, mas reavaliar o teste invalida a conclusão.

## Análise exploratória (notebook)

`notebooks/01_eda.ipynb` usa só treino e validação (o teste fica bloqueado) e lê `data/processed/` e `reports/`. As saídas já ficam salvas no arquivo; para abrir e rodar de novo:

```powershell
pip install -r requirements.txt
jupyter lab notebooks/01_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb   # roda de cima a baixo, sem abrir o Jupyter
```

Os gráficos são salvos em `reports/figuras/eda_*.png` (150 dpi). A seção 9 precisa de `models/best_model.joblib` (gerado por `python -m src.train --final`).

## Inferência em lote

```powershell
python -m src.predict_batch               # champion do MLflow Registry (cai no joblib se o Registry falhar)
python -m src.predict_batch --no-registry # só models/best_model.joblib
```

Grava `data/processed/predictions_latest.csv` (um bairro por linha, ordenado por `rank`, 1 = maior risco) com a previsão da semana seguinte à última semana dos dados. `risk_score = 50*prob_medio + 100*prob_alto` é um índice de 0 a 100, não uma probabilidade. A previsão vale para a última semana presente nos dados (hoje 2025-08-17), os casos chegam dos CSVs anuais com atraso e o sensor não alimenta o modelo.

## Sensor: ingestor MQTT e agregação semanal

As leituras do sensor (ESP32) NÃO alimentam o modelo; servem ao dashboard e à demonstração. Estação -> bairro em `config/stations_bairros.json` (edite com os `station_id` reais; os bairros precisam existir no painel).

```powershell
python -m src.ingest_mqtt --host localhost --port 1883   # assina antecedengue/estacoes/+/leituras (QoS 1); Ctrl+C encerra
python -m src.sensor_agg                                  # recalcula sensor_weekly (semana domingo a sábado em America/Recife)
python scripts/demo_sensor.py                             # demonstração sem broker (SQLite em memória)
pytest -m integration                                     # teste com Mosquitto real (pulado se não houver broker)
```

`DATABASE_URL` (Postgres em produção) e `MQTT_HOST`/`MQTT_PORT` vêm do `.env`; use `--database-url sqlite:///sensor.db` para testar localmente.

## API (FastAPI)

Pré-requisitos: `models/model_meta.json` e o modelo (champion no MLflow ou `models/best_model.joblib`); para `/predictions/latest`, rode antes `python -m src.predict_batch`.

```powershell
uvicorn api.main:app --reload          # http://localhost:8000/docs
```

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/model
curl "http://localhost:8000/predictions/latest?top=5"
curl "http://localhost:8000/predictions/latest?classe=alto&top=10"
curl "http://localhost:8000/bairros"
curl "http://localhost:8000/bairros/boa%20viagem"
curl "http://localhost:8000/sensor/weekly?bairro=BOA%20VIAGEM&desde=2025-02-01"
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "@exemplo_features.json"
```

`risk_score` é um índice de ordenação de 0 a 100, não calibrado (não é probabilidade de surto). As leituras do sensor são exibidas mas não entram na previsão. Variáveis: `DATABASE_URL` (banco do sensor), `API_CORS_ORIGINS` (origens do dashboard, separadas por vírgula).

## Dashboard (Streamlit)
O dashboard consome só a API. Em dois terminais, com o ambiente virtual ativo:
```
uvicorn api.main:app --port 8000
streamlit run app/dashboard.py
```
Abre em http://localhost:8501 com cinco abas: Mapa de risco, Ranking, Bairro, Sensor e Modelo. Variáveis: `API_URL` (padrão `http://localhost:8000`) e `SENSOR_FONTE` (`real` por padrão; com `simulado` ou `teste` a aba Sensor avisa que os dados não são de estações reais). Se a API estiver fora do ar, o dashboard mostra o endereço tentado.

Sempre se fala em "índice de risco" (0 a 100, não calibrado), com a semana base e a semana prevista no topo de cada aba; não é monitoramento em tempo real nem diagnóstico. O mapa usa os limites oficiais dos bairros (`app/assets/bairros.geojson`, ver `docs/DADOS.md`) e os tiles do mapa precisam de internet. Para refazer o GeoJSON: `python scripts/build_bairros_geojson.py`. Para gravar a persistência da validação em `models/model_meta.json` sem retreinar: `python scripts/patch_meta_persistencia.py` (novas execuções de `src.final` já gravam).
