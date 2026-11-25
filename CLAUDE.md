# AnteceDengue (G15) — contexto e decisões

## Projeto
- Previsão de risco de dengue por bairro do Recife. Trabalho da CESAR School que vale para Aprendizado de Máquina (AV2) e Sistemas Embarcados.
- Entrega: 11/12/2026 às 23:59, com relatório em PDF no template SBC e link deste repositório.
- Este repositório cobre só a parte de ML e MLOps. Não há ESP32 nem hardware (decisão do professor orientador, 25/11/2026): a aquisição é uma estação simulada que publica no MQTT dados reais da API Open-Meteo (ver "Decisões da estação simulada").

## Decisões de ML (não mudar sem avisar o Caio)
- Problema: classificação. Prever a classe de risco da semana t+1 por bairro: 0 = baixo, 1 = médio, 2 = alto.
- Rótulo: quantis 0.60 e 0.85 dos casos(t+1), calculados SÓ no treino.
- Unidade de análise: bairro x semana epidemiológica (semana começa no domingo, coluna week_start).
- Features: só informação do passado ou do presente (casos atuais, lags 1 a 3, médias móveis 4 e 8, tendência, média histórica expansiva por bairro, lags de clima 1/2/4/8, chuva acumulada 2/4/8, seno e cosseno da sazonalidade). Features do sensor NÃO entram no treino (ver "Decisões de ML (passo 5)").
- Validação: holdout cronológico (treino | validação 26 semanas | teste 26 semanas, com 1 semana de gap) e CV de janela expansiva com 5 splits. Proibido k-fold aleatório (vaza o futuro). O teste é usado uma única vez, no final.
- Seleção de modelo: F1-macro na CV. Métricas reportadas: F1-macro, balanced accuracy, recall da classe alto e matriz de confusão. Referência: baseline ingênuo de persistência (risco da semana t repetido em t+1).
- Modelos permitidos: LogisticRegression (baseline), KNN, DecisionTree, RandomForest, AdaBoost, MLP. Busca com RandomizedSearchCV usando a CV temporal. SVM e Gradient Boosting só com aprovação do professor.
- MLflow com 3 experimentos: 01-baseline, 02-comparacao-modelos, 03-otimizacao-hiperparametros. Modelo final registrado como antecedengue-risk-classifier.

## Dados
- Casos por bairro: CSVs anuais de dengue (2013 a 2025) do Portal de Dados Abertos do Recife (licença ODbL).
- Clima: InfoDengue (municipal, geocode 2611606) para temperatura e umidade; a API não traz chuva. Chuva: Open-Meteo (ERA5) em todo o período 2015 até PANEL_END, fonte única. É reanálise em grade (~25 km), NÃO é medição de estação (no relatório, chamar de "chuva estimada por reanálise"). O INMET A301 (Recife) só serve como verificação de sanidade, porque não tem chuva utilizável de 2022 em diante (2022 e 2023 vazios; 2024 e 2025 sem a estação). Comparação semanal Open-Meteo x INMET, anos usados 2015 a 2021 (341 semanas): Pearson 0,66 e Spearman 0,80 no total; por ano, Pearson de 0,58 (2019) a 0,82 (2017 e 2020). O Open-Meteo soma só ~0,42 da chuva do INMET (subestima o volume), então usar como índice relativo. Ver reports/clima_qualidade.md.
- Dados sintéticos servem só para testar o pipeline. Nunca usar em resultado, gráfico ou métrica do relatório. Se os nomes de colunas dos CSVs reais forem incertos, pergunte ao Caio em vez de assumir.
- Contrato do sensor (JSON): station_id, timestamp (UTC ISO com Z), latitude, longitude, temperature_c, relative_humidity, rainfall_mm (mm desde a leitura anterior), battery_voltage. Tópico MQTT: antecedengue/estacoes/<station_id>/leituras. Faixas válidas: temperatura -10 a 60, umidade 0 a 100, chuva >= 0. Leitura inválida é gravada com is_valid = false e não entra no modelo.

## Decisões de dados
- Caso = confirmado: CLASSI_FIN em 10, 11 ou 12 (anos 2021 a 2025) e 1 a 4 nos esquemas antigos. Descartados (5) e inconclusivos (8) não contam. Parâmetro em src/config.py (CASE_CODES).
- Período usado: 2015 a 2025. Os anos de 2013 e 2014 ficam fora (2014 está incompleto e quebraria a série).
- Data de referência do caso: data de início dos sintomas. Se estiver nula ou absurda (anterior em mais de 1 ano ao ano do arquivo, ou posterior à data de notificação), usa-se a data de notificação. Registros sem nenhuma data válida são descartados e contados.
- Cauda de 2025: casos recentes demoram a ser classificados (CLASSI_FIN nula ou 8), o que deixa as últimas semanas artificialmente baixas. PANEL_END = 2025-08-17 (config.py): última semana em que a fração de registros nulos/inconclusivos ainda fica dentro de referência (média jan–jun/2025 = 0,27%) + 5 pontos percentuais (limite 5,27%). O painel é cortado nessa semana. Ver reports/cauda_2025.md.

## Decisões de ML (passo 5)
- A chuva do treino é reanálise ERA5 (Open-Meteo), em escala diferente das leituras da estação simulada. Features do sensor NÃO entram no treino do modelo; o sensor só alimenta a demonstração ao vivo e o dashboard.
- Nulos de temperatura e umidade: preencher só com valores do passado (forward fill causal, limite de 2 semanas) antes de calcular os lags. O que restar de nulo fica para um SimpleImputer dentro do Pipeline do scikit-learn, ajustado só no treino.
- Classes desbalanceadas (~72/17/10): usar class_weight="balanced" quando o modelo suportar. Métrica de seleção: F1-macro; acompanhar também o recall da classe alto.
- Regra dos rótulos: baixo = casos <= q_mid; médio = casos <= q_high; alto = acima. Limiares estritamente crescentes (src/labels.py), ajustados só nos alvos do treino de cada split.
- Definições das features (src/features.py): linha t usa só semanas <= t; alvo = casos(t+1). Tendência = média móvel 4 - média móvel 8. Médias móveis e chuva acumulada incluem a semana t. Média histórica expansiva usa só semanas anteriores a t. Sazonalidade = seno/cosseno do dia do ano do meio da semana. As 8 primeiras semanas do painel são descartadas (histórico incompleto).
- Validação: o alvo da linha t cai na semana t+1. Linha de um conjunto não pode ter alvo na semana de início do conjunto seguinte; GAP_WEEKS semanas de linhas são excluídas entre os conjuntos.

## Decisões de ML (passo 6)
- Os limiares de rótulo ficam fixos, ajustados só no treino (hoje 0 e 1), e valem para todos os modelos. Isso mantém os resultados comparáveis. Na CV, cada fold usa os limiares ajustados no treino daquele fold (nunca nos alvos da validação do fold).
- Seleção de modelo: média do F1-macro nos folds 2 a 5 da CV de janela expansiva. O fold 1 é reportado, mas fica fora da média (treina só em 2015-2016 e não tem classe alto na validação).
- Comparar sempre contra a persistência no mesmo conjunto. Validação e teste têm distribuições de classe diferentes e não são comparáveis entre si.
- O conjunto de teste NÃO é usado nos experimentos 01 e 02 (guarda em código em src/train.py). MLflow local: MLFLOW_TRACKING_URI padrão sqlite:///mlflow.db (permite o Model Registry).
- Candidatos e class_weight: LogisticRegression, DecisionTree e RandomForest usam class_weight="balanced"; AdaBoost usa class_weight="balanced" no estimador-base (stump); KNN e MLP não suportam class_weight.

## Decisões de ML (passo 7)
- Otimizar só RandomForest e LogisticRegression (os dois que superaram a persistência).
- Na otimização, a CV de janela expansiva usa limiares fixos (0 e 1, do treino inteiro), porque o RandomizedSearchCV exige um y único. Limitação: em cada fold os limiares usam alvos que seriam da validação do fold. Seleção: média do F1-macro nos folds 2 a 5.
- O teste é avaliado UMA única vez (`--final`), com o modelo já escolhido; `reports/teste_final.json` trava reavaliações (`--force-reeval` invalida a conclusão).
- Conjunto de features: decidido por ablação (atual x atual + features da cidade, só passado); se a diferença for menor que o desvio entre folds, fica o conjunto mais simples.

## Decisões de uso (passo 9: inferência em lote)
- `python -m src.predict_batch` carrega o champion do MLflow Registry (ou `models/best_model.joblib` se o Registry estiver inacessível), confere a versão do scikit-learn contra `models/model_meta.json` e grava `data/processed/predictions_latest.csv`.
- Limitação 1: a previsão é feita sobre a última semana presente nos dados (hoje PANEL_END = 2025-08-17), então prevê a semana seguinte a essa data, não a semana atual do calendário.
- Limitação 2: os casos vêm de CSVs anuais do portal, que chegam com atraso; a previsão só se atualiza quando os CSVs forem atualizados.
- Limitação 3: as leituras do sensor NÃO alimentam o modelo (só a demonstração ao vivo e o dashboard).
- `risk_score = 50*prob_medio + 100*prob_alto` é um índice de 0 a 100 para ordenar bairros; não é probabilidade.
- As colunas de features da inferência são exatamente as de `model_meta.json`, na mesma ordem; se faltar alguma, a função falha com erro claro.

## Decisões do sensor (passo 10: ingestão MQTT)
- As leituras do sensor NÃO alimentam o modelo; servem ao dashboard e à demonstração da infraestrutura.
- A semana das leituras é calculada no fuso America/Recife (domingo a sábado), embora o timestamp chegue em UTC. Uma leitura de sábado 23:30 em Recife (domingo 02:30 UTC) pertence à semana que termina nesse sábado.
- A relação estação -> bairro vem de config/stations_bairros.json (station_id para bairro, nomes oficiais do painel); `src/stations.py` valida os bairros contra o painel. Estação sem bairro é ignorada na agregação, com aviso.
- sensor_readings guarda horários em UTC sem fuso; (station_id, ts) é único, então reenvios do QoS 1 são idempotentes (a primeira gravação prevalece). Leitura inválida é gravada com is_valid = false e invalid_reason; sem timestamp reconhecível (ts nulo) ela não entra na deduplicação.
- sensor_weekly: média das leituras válidas (todas as estações do bairro, ponderada por leitura), chuva = soma de rainfall_mm, menor tensão de bateria. A agregação apaga e recalcula as semanas afetadas.

## Decisões da API (passo 11)
- A API nunca chama a saída do modelo de "probabilidade de surto". O campo se chama risk_score e a documentação diz que é um índice de ordenação de 0 a 100, não calibrado.
- As leituras do sensor são exibidas (/bairros/{bairro}, /sensor/weekly), mas não entram na previsão. /predict recebe features explícitas; não lê o sensor.
- O modelo é carregado uma vez no lifespan (champion do Registry, com fallback para models/best_model.joblib); se não carregar, a API não sobe e informa o motivo. Aviso em log se a versão do scikit-learn diferir de model_meta.json.
- Acesso a CSVs e ao banco do sensor fica só em api/repository.py (o passo 13 troca o CSV por Postgres sem mexer nos endpoints). CORS: origens em API_CORS_ORIGINS (padrão: dashboard Streamlit em localhost:8501).
- URLs `postgresql://` são convertidas para `postgresql+psycopg2://` (o SQLAlchemy 2.1 usaria psycopg 3 por padrão).

## Registro de uso de IA
- Após cada passo, acrescentar uma entrada em docs/USO_DE_IA.md (data, passo, o que o Claude Code fez, o que o humano verificou). O grupo entrega uma declaração de uso de IA toda semana aos orientadores.

## Stack obrigatória
MLflow, Airflow (DAG semanal), MQTT com Mosquitto, Postgres, FastAPI, dashboard em Streamlit, tudo subindo com um único docker compose up. O modelo é salvo com joblib, e a versão do scikit-learn deve ser a mesma em todos os containers.

## Estrutura de pastas planejada
src/ (config.py, dados, features, rótulos, validação, modelos, treino, predição), api/, app/, dags/, embedded/ (README; o publicador está em src/api_publisher.py e scripts/sim_publisher.py), docker/, notebooks/, reports/, docs/, tests/.

## Convenções
- Python 3.11. SEED = 42. Constantes e caminhos centralizados em src/config.py.
- Identificadores de código em inglês. Docs, docstrings e mensagens para o usuário em português.
- Não deixar comentários (`#`) no código, nem de linha nem inline. A explicação vai na docstring (curta) ou no nome claro das variáveis.
- Testes com pytest. Todo passo termina com testes passando.
- Commits pequenos, mensagem clara. Nunca commitar segredos nem dados brutos grandes (usar .env e .gitignore).
- Não adicionar Co-Authored-By nem qualquer atribuição ao Claude nas mensagens de commit.

## Como trabalhar neste repositório
- Um passo por vez. Só considere o passo concluído quando os critérios de pronto estiverem verificados e você mostrar a evidência (saída de comando ou teste).
- Não instale dependências nem mude decisões acima sem avisar antes.
- Se algo estiver ambíguo, pergunte ao Caio em vez de inventar.

## Decisões do dashboard (passo 12)
- O dashboard (`streamlit run app/dashboard.py`) consome só a API (`API_URL`); nunca lê arquivos nem o modelo. Funções puras em `app/data.py`, cliente HTTP em `app/api_client.py`.
- Sempre "índice de risco" (0 a 100, não calibrado); nunca "probabilidade de surto". Probabilidades por classe aparecem com aviso de que não são calibradas.
- Toda tela com previsão mostra a semana base e a semana prevista (hoje 17/08/2025 e 24/08/2025) e que não é monitoramento em tempo real nem diagnóstico.
- Leituras do sensor são exibidas como monitoramento de microclima e não alimentam o modelo. Se vierem de dados simulados/de teste, o dashboard avisa (variável `SENSOR_FONTE`, pois a API não distingue).
- Mapa: limites oficiais dos bairros do portal (ODbL), `app/assets/bairros.geojson`; se faltar ou não cobrir os bairros, cai para ranking em barras com aviso. Paleta de uma só matiz (Oranges), classe sempre também em texto.
- A persistência na validação fica em `models/model_meta.json` (`persistencia_f1_macro`, `persistencia_recall_alto`) para a aba Modelo.

## Decisões do Docker Compose (passo 13)
- O `mlflow.db` local NÃO é montado nos containers (guarda caminhos absolutos do Windows nos artefatos). O MLflow do compose tem backend SQLite e artefatos em volume próprio (`mlflow-data`), com `--serve-artifacts`, e é alimentado por `scripts/seed_mlflow.py` (perfil `init`).
- O seed registra o champion existente (`models/best_model.joblib`) e as métricas do experimento 03 sem reexecutar o teste (os números do teste são só copiados de `model_meta.json`). É idempotente: se o alias `champion` já existe, não faz nada (`--force` registra outra versão). O container `trainer` (perfil `train`) roda só os experimentos 01, 02 e 03, nunca `--final`, e grava os relatórios em volume próprio, não no repositório.
- Segredos e configuração vão em `.env` (ignorado pelo git); `.env.example` é versionado. A senha do Postgres entra numa URL, então use só letras e números. Mosquitto anônimo (`allow_anonymous true`) é só para desenvolvimento.
- Uma imagem só (`Dockerfile`, python:3.11-slim, usuário sem privilégios), com `requirements-runtime.txt` e scikit-learn fixado em 1.9.1 (igual a `model_meta.json`; um teste confere). `models/` e `data/processed/` entram na API por montagem somente leitura.
- Portas: Postgres e MLflow só em 127.0.0.1. O Postgres do host já ocupava a 5432 nesta máquina, então a porta publicada é `POSTGRES_HOST_PORT` (padrão 5433). Dentro da rede do compose continua 5432.
- MLflow com `--workers 1` e `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false`: com os padrões ele subia vários workers e consumidores de jobs e passava de 2,4 GiB; assim fica perto de 370 MiB.
- O dashboard lê `SENSOR_FONTE` do ambiente do compose; com a estação simulada, suba com `SENSOR_FONTE=open-meteo docker compose --profile demo up -d` (padrão; `simulado` só para o modo sintético offline) (um serviço de perfil não consegue mudar o ambiente de outro). `scripts/sim_publisher.py` usa a API Open-Meteo por padrão (`--source api`); `--source synthetic` gera valores sorteados e serve só como fallback offline.
- A API carrega o modelo uma vez na partida: depois de rodar o seed pela primeira vez, reinicie a API (`docker compose restart api`), senão ela fica no fallback do joblib.

## Decisões do Airflow (passo 14)
- O Airflow roda no perfil `airflow` do compose (não pesa a pilha base): imagem oficial `apache/airflow:2.10.5-python3.11`, instalada com o arquivo de constraints oficial (`Dockerfile.airflow`), LocalExecutor, metadados num banco `airflow` separado dentro do mesmo Postgres. O admin vem de `AIRFLOW_ADMIN_USER` e `AIRFLOW_ADMIN_PASSWORD` no `.env`; sem senha padrão (o `airflow-init` aborta se faltarem).
- O Airflow 2.10 exige SQLAlchemy 1.4 e o projeto usa SQLAlchemy 2: as dependências do projeto ficam num virtualenv separado (`/home/airflow/pipeline-venv`, de `requirements-pipeline.txt`, com scikit-learn 1.9.1) e os DAGs chamam `$PIPELINE_PYTHON -m src...`. Assim nada quebra as dependências do Airflow e não há lógica duplicada nos DAGs.
- DAGs (pasta `dags/`), todos com `retries=2`, `catchup=False`, fuso America/Recife: `antecedengue_dados` (segunda 05:00: ingestão, painel, clima, validação de qualidade, publicação), `antecedengue_semanal` (segunda 06:00: agrega_sensor, inferencia_em_lote, registra_monitoramento) e `antecedengue_treino` (manual, parâmetro `n_iter`). O treino NUNCA roda `--final`; a promoção de modelo é manual (mover o alias champion no MLflow).
- Idempotência: sem `refresh=true` o DAG de dados não baixa os CSVs que já existem (precisa de internet só com refresh ou arquivo faltando); `data/processed` ganha cópias `.bak` antes da preparação e volta a elas se a validação falhar (duplicata de (bairro, week_start), semanas faltando, nulos fora do esperado ou PANEL_END incoerente). A inferência substitui as previsões da mesma semana base.
- Previsões em lote vão também para a tabela `predictions` do Postgres (`python -m src.predict_batch --gravar-banco`, chave (bairro, week_start)). A API lê do Postgres primeiro e cai para o CSV; `/predictions/latest` informa a origem no campo `fonte`.
- Monitoramento: um run por execução no experimento `04-monitoramento-semanal` (bairros, distribuição das classes previstas, semana base). Não avalia o modelo.
- Os relatórios gerados pelos DAGs ficam no volume `airflow-reports`, não na pasta `reports/` do repositório. Portas: Airflow em `127.0.0.1:${AIRFLOW_HOST_PORT:-8080}` (nesta máquina o 8080 do host é de outro serviço do Windows, então o `.env` usa 8081).
- Arquivos `.sh` e `.conf` têm fim de linha LF (`.gitattributes`), senão quebram dentro dos containers.

## Decisões do dashboard: identidade e login
- Marca: logo SVG próprio (`app/assets/logo.svg`, gota com tendência de alta e ondas de alerta) embutido no HTML; cabeçalho em verde-azulado profundo com o nome "AnteceDengue". Sem fontes nem imagens externas.
- Login (`app/auth.py`): usuário e senha só do ambiente (`DASHBOARD_USER`, `DASHBOARD_PASSWORD`, no `.env`). Sem credenciais válidas, ou com a senha de exemplo, o acesso fica fechado (nunca aberto). Comparação em tempo constante e bloqueio de 30 s após 5 falhas por sessão. Protege só a interface; a API continua aberta na porta 8000.
- `.gitignore` tem a seção "# Embarcados e segredos" (secrets.h, .pio/, .env.*, *.bak; as regras de secrets.h e .pio/ são só precaução); `.env.example` continua versionado.

## Limitações conhecidas
- O IC do teste vem do bootstrap em blocos de 4 semanas ([+0,021, +0,054]); com blocos de 1 semana fica [+0,017, +0,061] e com 2 semanas [+0,020, +0,057].
- As estatísticas da EDA só reproduzem excluindo as 8 primeiras semanas do painel; sem essa exclusão os limiares viram (0, 2) e a persistência 76,1%.
- Mosquitto anônimo e dashboard com login simples (usuário e senha do `.env`) são só para desenvolvimento e demonstração; a API não tem autenticação. API e dashboard publicam em 127.0.0.1 por padrão (`BIND_ADDRESS`).
- O modelo final e os dados processados são versionados; `--final` não pode ser repetido (a guarda do teste recusa).

## Decisões da estação simulada (Open-Meteo)
- Decisão do professor orientador (25/11/2026): o projeto não usa ESP32 nem hardware. A aquisição é uma estação simulada alimentada por dados da API Open-Meteo, publicados via MQTT. Texto padrão: "estação simulada alimentada por dados da API Open-Meteo, publicados via MQTT". Sensores reais ficam como trabalho futuro.
- Fluxo: API Open-Meteo -> publicador (`src/api_publisher.py`, `scripts/sim_publisher.py --source api`) -> MQTT/Mosquitto -> ingestor -> Postgres -> sensor_weekly -> `src/export_sensor_csv.py` -> `data/processed/sensor_semanal.csv`. Contrato do payload e tópico não mudaram. Esse CSV NÃO entra no treino.
- Coordenadas por estação em `config/stations_bairros.json` (chave "coordinates"). Timestamp publicado = instante da consulta (UTC); rainfall_mm = precipitação do bloco de 15 min da API, contada uma vez; battery_voltage é valor fixo sem sentido físico (4.0). Máximo de 1 chamada por estação por minuto, timeout e repetição com espera crescente; falha da API pula a leitura. Backfill horário de 7 dias via `past_days`.
- Open-Meteo: crédito obrigatório "Weather data by Open-Meteo.com" (https://open-meteo.com) em README, docs/DADOS.md e rodapé do dashboard. A precipitação é de modelo/reanálise, não observação, e a API gratuita é só para uso não comercial.
- Testes nunca acessam a internet (a API é simulada com mocks). `SENSOR_FONTE` padrão é `open-meteo`.
- DAG `antecedengue_semanal`: a última tarefa (`exporta_csv_sensor`) gera o CSV; no compose, `docker compose --profile export run --rm export-sensor`.

## Decisões da projeção sazonal 2026
- Orientação do professor: treino até 2024, teste em 2025 (já coberto pelo split semanal atual) e projeção sazonal mensal para 2026. É projeção de padrão sazonal, nunca previsão verificada; o texto da API e do dashboard diz isso (campo `aviso` fixo).
- Código em `src/projecao.py` (`python -m src.projecao`) e `src/projecao_figuras.py`. Mês da semana = mês do domingo de início; só meses completos (último: 2025-07); casos/mês = casos_brutos / domingos_do_mês * 52/12. Limiares q0.60/q0.85 sobre os valores bairro x mês do treino (`labels.fit_thresholds`). Método escolhido só pelo Backtest A (treino até 2023 -> 2024); o Backtest B (até 2024 -> 2025, jan a jul) é calculado uma vez e não participa da escolha. Todo método recusa histórico com o ano projetado (ValueError).
- Experimento MLflow `05-projecao-sazonal` (o 04 já era o monitoramento semanal). Saídas versionadas (exceção no .gitignore): `data/processed/projecao_2026_mensal.csv` e `projecao_2026_meta.json`; relatório em `reports/projecao_sazonal.md`.
- Passo 0 (25/11/2026): portal sem dados novos além de ago/2025 (tamanhos idênticos); 2013 e 2014 continuam fora. Painel inalterado, métricas do modelo semanal NÃO recalculadas.
- Limitações: anos epidêmicos mudam a magnitude; sem clima futuro; ago a dez/2025 não entram (cauda), então há um degrau entre jul e ago na curva de 2026; confiança = consistência da classe entre anos, não intervalo estatístico.
