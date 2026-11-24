"""DAG semanal de dados (segunda 05:00, America/Recife): ingestão, painel, clima, validação e publicação.

Idempotente: sem refresh, os CSVs já baixados não são baixados de novo, e o painel e o clima são
reconstruídos a partir dos brutos. Se a validação falhar, os arquivos de data/processed voltam à cópia
de segurança feita antes da preparação.
Só precisa de internet com refresh=true ou se faltar algum arquivo bruto.
"""
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator

from common import DAG_KWARGS, PROJECT_DIR, py

REFRESH = "{% if params.refresh %}--refresh{% endif %}"

with DAG(
    dag_id="antecedengue_dados",
    description="Ingestão, painel bairro x semana, clima semanal e validação de qualidade",
    schedule="0 5 * * 1",
    params={"refresh": Param(False, type="boolean", description="Baixar os CSVs e o clima de novo")},
    tags=["antecedengue", "dados"],
    **DAG_KWARGS,
) as dag:
    ingestao = BashOperator(
        task_id="ingestao", cwd=PROJECT_DIR,
        bash_command=py(f"-m src.pipeline_dados ingestao {REFRESH} && ") + py("-m src.pipeline_dados resumo raw"))
    preparacao = BashOperator(
        task_id="preparacao_painel", cwd=PROJECT_DIR,
        bash_command=py("-m src.pipeline_dados backup && ") + py("scripts/build_panel.py && ")
        + py("-m src.pipeline_dados resumo panel"))
    clima = BashOperator(
        task_id="clima_semanal", cwd=PROJECT_DIR,
        bash_command=py(f"-m src.pipeline_dados clima {REFRESH} && ") + py("-m src.pipeline_dados resumo clima"))
    validacao = BashOperator(
        task_id="validacao_qualidade", cwd=PROJECT_DIR, bash_command=py("-m src.pipeline_dados validar"))
    disponibilizacao = BashOperator(
        task_id="disponibiliza_processed", cwd=PROJECT_DIR, bash_command=py("-m src.pipeline_dados publicar"))

    ingestao >> preparacao >> clima >> validacao >> disponibilizacao
