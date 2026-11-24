"""DAG de treino (sem agendamento, disparo manual): roda os experimentos 01, 02 e 03 e registra no MLflow.

NUNCA roda --final: o conjunto de teste foi avaliado uma única vez. A promoção de modelo é manual
(registrar uma nova versão e mover o alias champion no MLflow). Parâmetro: n_iter da busca do experimento 03.
"""
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator

from common import DAG_KWARGS, PROJECT_DIR, py

with DAG(
    dag_id="antecedengue_treino",
    description="Experimentos 01, 02 e 03 (nunca --final) registrados no MLflow",
    schedule=None,
    params={"n_iter": Param(30, type="integer", minimum=1, maximum=100,
                            description="Iterações da busca de hiperparâmetros (experimento 03)")},
    tags=["antecedengue", "treino"],
    **DAG_KWARGS,
) as dag:
    exp01 = BashOperator(task_id="exp01_baseline", cwd=PROJECT_DIR, bash_command=py("-m src.train --exp 01"))
    exp02 = BashOperator(task_id="exp02_comparacao", cwd=PROJECT_DIR, bash_command=py("-m src.train --exp 02"))
    exp03 = BashOperator(task_id="exp03_otimizacao", cwd=PROJECT_DIR,
                         bash_command=py("-m src.train --exp 03 --n-iter {{ params.n_iter }}"))

    exp01 >> exp02 >> exp03
