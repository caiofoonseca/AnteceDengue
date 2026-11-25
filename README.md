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

## Arquivos que já vêm no repositório

Para o clone rodar sem baixar dados nem retreinar, o repositório versiona: `models/best_model.joblib` (modelo final, ~45 MB), `models/model_meta.json`, `data/processed/panel.csv`, `data/processed/clima_semanal.csv` e `data/processed/predictions_latest.csv`. Ficam de fora (`.gitignore`): `data/raw/`, `data/processed/manifest.json`, cópias `.bak`, `.env`, `mlflow.db` e `mlruns/`.

O modelo versionado é o **modelo final**: foi reajustado em treino + validação e o conjunto de teste foi avaliado uma única vez. Por isso `python -m src.train --final` **não pode ser repetido**: o `reports/teste_final.json` trava a reavaliação (a guarda existe para o modelo não ser ajustado olhando o teste; `--force-reeval` invalida a conclusão). Para regenerar os dados brutos use os scripts de `docs/DADOS.md`; os experimentos 01 a 03 podem ser refeitos.

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

## Estação simulada: Open-Meteo, MQTT e agregação semanal

Não há sensor físico nem ESP32 (decisão do professor orientador, 25/11/2026): a aquisição é uma **estação simulada alimentada por dados da API Open-Meteo, publicados via MQTT**. Fluxo: API Open-Meteo -> publicador (`scripts/sim_publisher.py`, `--source api`, padrão) -> MQTT/Mosquitto -> ingestor -> Postgres -> `sensor_weekly` -> `data/processed/sensor_semanal.csv`. Sensores reais ficam como trabalho futuro. São 8 estações simuladas (`recife-001` a `recife-008`: BOA VIAGEM, VARZEA, BOA VISTA, CASA FORTE, IPUTINGA, PINA, AFOGADOS e IBURA), com coordenadas do centroide de cada bairro calculado a partir de `app/assets/bairros.geojson`; cada estação faz no máximo 1 consulta por minuto à Open-Meteo.

As leituras NÃO alimentam o modelo (nem o `sensor_semanal.csv`); servem ao dashboard e à demonstração da infraestrutura. A precipitação da Open-Meteo vem de modelo/reanálise, não é observação, e a API gratuita é só para uso não comercial. **Weather data by [Open-Meteo.com](https://open-meteo.com)** (CC BY 4.0).

O CSV semanal (bairro, semana_inicio, temp_media, umid_media, chuva_mm_soma, n_leituras, fonte) é gerado por `python -m src.export_sensor_csv` (no compose: `docker compose --profile export run --rm export-sensor`; no Airflow, última tarefa do DAG semanal). `--source synthetic` do publicador gera valores sorteados e serve só como fallback offline. Estação -> bairro em `config/stations_bairros.json` (edite com os `station_id` reais; os bairros precisam existir no painel).

```powershell
python -m src.ingest_mqtt --host localhost --port 1883   # assina antecedengue/estacoes/+/leituras (QoS 1); Ctrl+C encerra
python -m src.sensor_agg                                  # recalcula sensor_weekly (semana domingo a sábado em America/Recife)
python scripts/demo_sensor.py                             # demonstração sem broker (SQLite em memória)
pytest -m integration                                     # teste com Mosquitto real (pulado se não houver broker)
```

`DATABASE_URL` (Postgres em produção) e `MQTT_HOST`/`MQTT_PORT` vêm do `.env`; use `--database-url sqlite:///sensor.db` para testar localmente.

## Projeção sazonal de 2026 (por bairro e mês)

Por orientação do professor, além da previsão semanal (treino até jul/2024, validação ago/2024 a fev/2025, teste fev a ago/2025), o projeto traz uma **projeção sazonal mensal de risco para 2026**. Não existem casos reais de 2026: é a projeção do **padrão sazonal do histórico**, não uma previsão verificada e não é número exato de casos. Não captura surtos e não usa clima futuro. O modelo semanal, o teste final e as métricas já reportadas não mudam.

```powershell
python -m src.projecao            # backtests A e B, escolha do método, CSV, metadados, relatório e MLflow (05-projecao-sazonal)
python -m src.projecao_figuras    # figuras em reports/figuras/projecao_*.png
```

- Mês de uma semana = mês do domingo de início; só meses completos entram (último: julho/2025). Casos/mês padronizados: `casos_brutos / domingos_do_mês * 52/12`.
- Classes 0/1/2 com limiares mensais q0.60 e q0.85 ajustados só no histórico real. Candidatos: climatologia, mesmo mês do último ano (baseline), média ponderada por recência (meia-vida de 1, 2 e 3 anos) e RandomForest só com calendário e histórico. O método é escolhido pelo **Backtest A** (treino até 2023, projeta 2024); o **Backtest B** (treino até 2024, projeta jan a jul/2025) é calculado uma vez e só informa quanto confiar.
- Saídas versionadas: `data/processed/projecao_2026_mensal.csv` (bairro, mes, casos_esperados, classe_risco, p25, p75, confianca, metodo, ultima_data_real_usada) e `projecao_2026_meta.json`. Relatório com as tabelas de métricas: `reports/projecao_sazonal.md`.
- API: `GET /projecao/2026?bairro=&mes=` (campo `aviso` fixo). Dashboard: aba "Projeção 2026" (aviso no topo, seletor de mês, mapa, ranking, curva sazonal da cidade com faixa p25 a p75 e métricas do Backtest B).

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
Abre em http://localhost:8501 com seis abas: Mapa de risco, Ranking, Bairro, Projeção 2026, Sensor e Modelo. Variáveis: `API_URL` (padrão `http://localhost:8000`) e `SENSOR_FONTE` (`open-meteo` por padrão: a aba Sensor mostra o selo "estação simulada, dados Open-Meteo"; com `simulado`, `teste` ou `sintetico` avisa que os dados são sintéticos). Se a API estiver fora do ar, o dashboard mostra o endereço tentado. O acesso exige login: defina `DASHBOARD_USER` e `DASHBOARD_PASSWORD` no `.env` (sem esses valores, ou com a senha de exemplo, o acesso fica fechado). O login protege só a interface do dashboard; a API (porta 8000) tem as regras dela. A identidade visual (logo em `app/assets/logo.svg`, tema em `.streamlit/config.toml` e `app/assets/style.css`) não usa fontes nem imagens externas.

Sempre se fala em "índice de risco" (0 a 100, não calibrado), com a semana base e a semana prevista no topo de cada aba; não é monitoramento em tempo real nem diagnóstico. O mapa usa os limites oficiais dos bairros (`app/assets/bairros.geojson`, ver `docs/DADOS.md`) e os tiles do mapa precisam de internet. Para refazer o GeoJSON: `python scripts/build_bairros_geojson.py`. Para gravar a persistência da validação em `models/model_meta.json` sem retreinar: `python scripts/patch_meta_persistencia.py` (novas execuções de `src.final` já gravam).

## Docker Compose (pilha completa, sem Airflow)
Serviços: mosquitto (1883), postgres, mlflow (5000), ingestor MQTT, api (8000) e dashboard (8501). Ordem de uso:
```
python scripts/setup_env.py                # cria o .env e gera as senhas (Postgres, Airflow, login do dashboard)
python scripts/doctor.py                   # confere arquivos, Docker, .env, portas e riscos de configuração
docker compose up --build -d               # sobe tudo e espera os healthchecks
docker compose --profile init run --rm seed-mlflow   # registra o champion no MLflow do compose (uma vez)
docker compose restart api                 # a API passa a carregar o modelo do Registry
docker compose ps                          # todos devem estar healthy
```
Pré-requisito: `models/` e `data/processed/` gerados (a API os monta somente leitura).

- Estação simulada (dados da Open-Meteo via MQTT): `docker compose --profile demo up -d` (`SENSOR_FONTE=open-meteo`, padrão). Depois, `docker compose exec api python -m src.sensor_agg` agrega as leituras por semana e bairro e `docker compose --profile export run --rm export-sensor` gera `data/processed/sensor_semanal.csv`. Precisa de internet.
- Reexecutar os experimentos 01, 02 e 03 (nunca `--final`): `docker compose --profile train run --rm trainer` (relatórios no volume `trainer-reports`).
- Teste de integração do ingestor contra o Mosquitto do compose: `MQTT_HOST=localhost pytest -m integration`.
- Postgres do compose em `127.0.0.1:5433` (variável `POSTGRES_HOST_PORT`); MLflow em http://localhost:5000.
- Logs: `docker compose logs -f ingestor`. Parar: `docker compose down` (mantém os dados). Apagar também os volumes (banco, MLflow, Mosquitto): `docker compose down -v`.
- **Rede:** API e dashboard publicam só em `127.0.0.1`. Para liberar na rede, defina `BIND_ADDRESS=0.0.0.0` no `.env` (a API não tem autenticação e o login do dashboard é simples; use só em rede de demonstração). O Mosquitto fica em `0.0.0.0:1883` para aceitar um publicador de outra máquina da rede (com a estação simulada, o publicador roda no próprio compose). As portas do host são configuráveis: `API_HOST_PORT`, `DASHBOARD_HOST_PORT`, `MLFLOW_HOST_PORT`, `MQTT_HOST_PORT`, `POSTGRES_HOST_PORT`.
- **Login do dashboard:** usuário em `DASHBOARD_USER` (padrão `g15`) e senha em `DASHBOARD_PASSWORD` (gerada pelo `setup_env.py`). `DASHBOARD_AUTH=off` desliga o login só para demonstração (padrão: ligado).
- O Mosquitto aceita conexões anônimas (só para desenvolvimento). A pilha usa cerca de 0,8 GiB no total; nenhum serviço passa de 1 GiB.

## Airflow (perfil `airflow`) e script de demonstração
O Airflow fica fora da pilha base. Defina no `.env` `AIRFLOW_ADMIN_USER`, `AIRFLOW_ADMIN_PASSWORD`, `AIRFLOW_FERNET_KEY` e `AIRFLOW_SECRET_KEY` (veja `.env.example`) e rode:
```
docker compose --profile airflow up --build -d
```
A interface abre em http://localhost:8080 (ou na porta de `AIRFLOW_HOST_PORT`). DAGs, em `dags/`:

| DAG | Quando | O que faz |
|---|---|---|
| `antecedengue_dados` | segunda 05:00 | ingestão (pula o download se os CSVs existem; `refresh=true` baixa de novo), painel, clima, validação de qualidade, publicação em `data/processed` |
| `antecedengue_semanal` | segunda 06:00 | agrega o sensor, inferência em lote (CSV e tabela `predictions` no Postgres) e run de monitoramento no MLflow |
| `antecedengue_treino` | manual | experimentos 01, 02 e 03 (nunca `--final`); parâmetro `n_iter` |

Testar um DAG sem esperar o agendamento: `docker compose --profile airflow exec airflow-scheduler airflow dags test antecedengue_semanal 2026-11-24` (o de treino aceita `--conf '{"n_iter": 2}'`). Testes dos DAGs dentro do container: `docker compose --profile airflow exec -w /opt/airflow/project airflow-scheduler python -m pytest tests/test_dags.py`. Só o download (`refresh=true` ou arquivo faltando) precisa de internet.

**Demonstração em um comando** (sobe a pilha, semeia o MLflow se preciso, reinicia a API, liga a estação simulada (Open-Meteo via MQTT), gera o CSV semanal e imprime as URLs):
```
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1 [-Airflow]
scripts/demo.sh [--airflow]
```
Para derrubar: `scripts\demo.ps1 -Down` (mantém os dados) ou `-Down -Volumes` (apaga os volumes); no bash, `scripts/demo.sh --down [--volumes]`.
