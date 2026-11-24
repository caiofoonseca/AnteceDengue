"""DAG semanal de inferência (segunda 06:00, America/Recife): agrega o sensor, prevê e registra o monitoramento.

Idempotente: a agregação apaga e recalcula as semanas afetadas, a inferência substitui as previsões da
mesma semana base no Postgres (e regrava o CSV) e o monitoramento cria um run novo no MLflow a cada execução.
As leituras do sensor NÃO alimentam o modelo; a agregação serve ao dashboard.
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

    agrega_sensor >> inferencia >> monitoramento
