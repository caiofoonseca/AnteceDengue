"""DAG semanal de inferência (segunda 06:00, America/Recife): agrega a estação simulada, prevê, registra o monitoramento
e exporta o CSV semanal da estação (data/processed/sensor_semanal.csv).

Idempotente: a agregação apaga e recalcula as semanas afetadas, a inferência substitui as previsões da
mesma semana base no Postgres (e regrava o CSV) e o monitoramento cria um run novo no MLflow a cada execução.
As leituras da estação simulada NÃO alimentam o modelo; a agregação e o CSV servem ao dashboard e à inferência recente.
"""
from airflow import DAG
from airflow.operators.bash import BashOperator

from common import DAG_KWARGS, PROJECT_DIR, py

with DAG(
    dag_id="antecedengue_semanal",
    description="Agregação do sensor, inferência em lote (CSV e Postgres) e monitoramento no MLflow",
    schedule="0 6 * * 1",
    tags=["antecedengue", "inferencia"],
    **DAG_KWARGS,
) as dag:
    agrega_sensor = BashOperator(task_id="agrega_sensor", cwd=PROJECT_DIR, bash_command=py("-m src.sensor_agg"))
    inferencia = BashOperator(task_id="inferencia_em_lote", cwd=PROJECT_DIR,
                              bash_command=py("-m src.predict_batch --gravar-banco"))
    monitoramento = BashOperator(task_id="registra_monitoramento", cwd=PROJECT_DIR,
                                 bash_command=py("-m src.monitoring"))

    exporta_csv = BashOperator(task_id="exporta_csv_sensor", cwd=PROJECT_DIR,
                               bash_command=py("-m src.export_sensor_csv"))

    agrega_sensor >> inferencia >> monitoramento >> exporta_csv
