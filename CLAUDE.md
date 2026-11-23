# AnteceDengue (G15) — contexto e decisões

## Projeto
- Previsão de risco de dengue por bairro do Recife. Trabalho da CESAR School que vale para Aprendizado de Máquina (AV2) e Sistemas Embarcados.
- Entrega: 11/12/2026 às 23:59, com relatório em PDF no template SBC e link deste repositório.
- Este repositório cobre só a parte de ML e MLOps. O sensor (ESP32) é feito por outra equipe, que só publica mensagens MQTT.

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
- A chuva do treino é reanálise ERA5 (Open-Meteo), em escala diferente do pluviômetro do ESP32. Features do sensor NÃO entram no treino do modelo; o sensor só alimenta a demonstração ao vivo e o dashboard.
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

## Registro de uso de IA
- Após cada passo, acrescentar uma entrada em docs/USO_DE_IA.md (data, passo, o que o Claude Code fez, o que o humano verificou). O grupo entrega uma declaração de uso de IA toda semana aos orientadores.

## Stack obrigatória
MLflow, Airflow (DAG semanal), MQTT com Mosquitto, Postgres, FastAPI, dashboard em Streamlit, tudo subindo com um único docker compose up. O modelo é salvo com joblib, e a versão do scikit-learn deve ser a mesma em todos os containers.

## Estrutura de pastas planejada
src/ (config.py, dados, features, rótulos, validação, modelos, treino, predição), api/, app/, dags/, embedded/ (simulador), docker/, notebooks/, reports/, docs/, tests/.

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
