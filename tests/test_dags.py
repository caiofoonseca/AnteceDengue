import re
from pathlib import Path

import pytest

DAGS = Path(__file__).resolve().parent.parent / "dags"
ESPERADO = {
    "antecedengue_dados": {"ingestao": [], "preparacao_painel": ["ingestao"], "clima_semanal": ["preparacao_painel"],
                           "validacao_qualidade": ["clima_semanal"], "disponibiliza_processed": ["validacao_qualidade"]},
    "antecedengue_semanal": {"agrega_sensor": [], "inferencia_em_lote": ["agrega_sensor"],
                             "registra_monitoramento": ["inferencia_em_lote"]},
    "antecedengue_treino": {"exp01_baseline": [], "exp02_comparacao": ["exp01_baseline"],
                            "exp03_otimizacao": ["exp02_comparacao"]},
}
AGENDA = {"antecedengue_dados": "0 5 * * 1", "antecedengue_semanal": "0 6 * * 1", "antecedengue_treino": None}


def test_dags_nunca_rodam_final_e_declaram_ids_e_agendas():
    for dag_id, agenda in AGENDA.items():
        texto = (DAGS / f"{dag_id}.py").read_text(encoding="utf-8")
        assert f'dag_id="{dag_id}"' in texto
        assert "--final" not in texto.replace("nunca --final", "").replace("NUNCA roda --final", "").replace(
            "(nunca --final)", "")
        esperado = f'schedule="{agenda}"' if agenda else "schedule=None"
        assert esperado in texto
    comum = (DAGS / "common.py").read_text(encoding="utf-8")
    assert '"retries": 2' in comum and "catchup" in comum and "America/Recife" in comum
    assert re.search(r'"catchup": False', comum)


def test_dagbag_sem_erros_de_importacao():
    pytest.importorskip("airflow")
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(DAGS), include_examples=False)
    assert bag.import_errors == {}
    assert set(ESPERADO) <= set(bag.dag_ids)


def test_dependencias_retries_e_fuso_dos_dags():
    pytest.importorskip("airflow")
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(DAGS), include_examples=False)
    for dag_id, tarefas in ESPERADO.items():
        dag = bag.get_dag(dag_id)
        assert {t.task_id for t in dag.tasks} == set(tarefas)
        for task_id, upstream in tarefas.items():
            task = dag.get_task(task_id)
            assert sorted(task.upstream_task_ids) == sorted(upstream)
            assert task.retries == 2
        assert dag.catchup is False
        assert str(dag.timezone) == "America/Recife"
    assert bag.get_dag("antecedengue_treino").schedule_interval is None
    assert bag.get_dag("antecedengue_treino").params["n_iter"] == 30
    assert bag.get_dag("antecedengue_dados").params["refresh"] is False
