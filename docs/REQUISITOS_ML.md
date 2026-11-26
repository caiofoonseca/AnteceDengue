# Rastreabilidade dos requisitos de ML

Mapa entre cada entrega de Aprendizado de Máquina e a evidência no repositório (arquivo, comando ou experimento). Os números vêm dos relatórios versionados; nada aqui foi recalculado.

| # | Requisito | Onde está | Como reproduzir |
|---|-----------|-----------|-----------------|
| 1 | Problema e dataset claros | `README.md`, `docs/DADOS.md`, `reports/dados_inspecao.md`, `reports/painel_qualidade.md` | `python -m src.pipeline_dados` |
| 2 | Análise exploratória | `reports/figuras/eda_*.png`, `notebooks/01_eda.ipynb` | abrir o notebook |
| 3 | Pré-processamento e features | `src/features.py`, `src/labels.py`, Pipeline com `SimpleImputer` em `src/models.py` | `pytest tests/test_features.py` |
| 4 | Modelos e comparação | MLflow `01-baseline`, `02-comparacao-modelos`; `reports/metricas_comparacao.csv`, `reports/figuras/f1_macro_comparacao.png` | `python -m src.train --exp 01` e `--exp 02` |
| 5 | Otimização e validação | MLflow `03-otimizacao-hiperparametros`; `reports/otimizacao_resumo.md`, `reports/busca_rf.csv`, `reports/busca_logreg.csv` | `python -m src.train --exp 03` |
| 6 | Avaliação e análise de erros | `reports/teste_final.md`, `reports/figuras/cm_final_teste.png`, `roc_final_teste.png`, `gap_overfitting.png` | ver seção 6 |
| 7 | Modelo integrado ao pipeline, consumindo dados novos do simulador | `src/predict_batch.py`, `src/predict_live.py`, DAG `antecedengue_semanal`, API `/predictions/live`, aba Sensor | ver seção 7 |

## 1. Problema e dataset (bootstrap)

- Problema: classificação do risco (0 baixo, 1 médio, 2 alto) de dengue por bairro do Recife na semana t+1.
- Dataset de partida (bootstrap): `data/processed/panel.csv` (casos confirmados por bairro e semana epidemiológica, 2015 a PANEL_END) e `data/processed/clima_semanal.csv` (temperatura e umidade InfoDengue; chuva estimada por reanálise Open-Meteo/ERA5).
- Dados novos: a estação simulada publica leituras reais da API Open-Meteo no MQTT; o ingestor grava no Postgres e a agregação semanal alimenta o dashboard e a inferência ao vivo. O CSV `data/processed/sensor_semanal.csv` é a exportação dessa série. Essas leituras NÃO entram no treino.

## 4 e 5. Validação: por que janela expansiva e não k-fold

Os dados são uma série temporal por bairro. O k-fold aleatório colocaria semanas futuras no treino de folds que avaliam semanas passadas (vazamento do futuro). Por isso o projeto usa holdout cronológico (treino, validação de 26 semanas, teste de 26 semanas, com 1 semana de gap) e validação cruzada de janela expansiva com 5 splits (`src/validation.py`). A validação cruzada "quando aplicável" é atendida dessa forma, que respeita a ordem do tempo.

## 6. Overfitting, underfitting e erros

- Overfitting: `reports/figuras/gap_overfitting.png` compara treino e validação por modelo; `reports/curva_aprendizado_final.csv` e `reports/figuras/curva_aprendizado_final.png` mostram a curva de aprendizado do modelo final.
- Underfitting: os modelos simples (regressão logística, árvore rasa) servem de referência e ficam abaixo do RandomForest; a persistência é o piso.
- Erros: matrizes de confusão (`cm_*.png`), recall da classe alto e curvas ROC por modelo.
- Métricas de regressão (resíduos, RMSE) não se aplicam: o problema é de classificação.
- Teste final: usado uma única vez (`reports/teste_final.json` trava reavaliações). F1-macro 0,611 contra 0,570 da persistência, com IC95% da diferença [+0,021, +0,054] (bootstrap em blocos de 4 semanas).

## 7. Modelo no pipeline com dados novos do simulador

Dois caminhos, ambos no DAG semanal `antecedengue_semanal` (segunda 06:00):

1. Inferência em lote (oficial): `python -m src.predict_batch --gravar-banco`. Usa o champion do MLflow Registry, casos e clima do painel; grava `predictions_latest.csv` e a tabela `predictions`.
2. Inferência ao vivo (demonstração): `python -m src.predict_live`. Tarefa `inferencia_ao_vivo`, depois de `agrega_sensor`. Constrói a série semanal do município a partir de `sensor_weekly` (semanas completas, domingo a sábado em Recife), calcula as features de clima do modelo (lags 1/2/4/8 e chuva acumulada 2/4/8) e as combina com as features de casos da última semana do painel real. Grava `predictions_live.csv` e a tabela `predictions_live`. API: `GET /predictions/live`. Dashboard: aba Sensor.

Limitações declaradas (também no dashboard e na API):

- A semana base dos casos (PANEL_END) não coincide com a semana do clima da estação; os casos chegam com atraso.
- O clima de treino (InfoDengue + ERA5) e o da estação (Open-Meteo em ponto) têm escalas diferentes, sobretudo a chuva.
- O modelo não foi treinado nem avaliado com dados da estação; por isso a saída ao vivo é demonstração do pipeline, não previsão operacional. O índice de risco (0 a 100) não é calibrado e não é probabilidade de surto.
