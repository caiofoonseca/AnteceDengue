import json

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src import db, monitoring
from src import pipeline_dados as pdd


def painel(semanas=6, bairros=("A", "B")):
    datas = pd.date_range("2025-07-06", periods=semanas, freq="7D")
    return pd.DataFrame([{"bairro": b, "week_start": d, "casos": i} for b in bairros for i, d in enumerate(datas)])


def clima(painel_df):
    datas = pd.date_range(painel_df["week_start"].min(), periods=painel_df["week_start"].nunique(), freq="7D")
    return pd.DataFrame({"week_start": datas, "temp_media": 28.0, "umid_media": 70.0, "chuva_mm": 5.0})


def fim(p):
    return str(p["week_start"].max().date())


def test_painel_valido_passa():
    p = painel()
    assert pdd.validate(p, clima(p), fim(p)) == []


def test_detecta_duplicata():
    p = painel()
    p = pd.concat([p, p.iloc[[0]]], ignore_index=True)
    assert any("duplicadas" in x for x in pdd.validate(p, clima(p), fim(p)))


def test_detecta_semana_faltando_e_bairro_incompleto():
    p = painel()
    p = p.drop(p[(p["bairro"] == "A") & (p["week_start"] == pd.Timestamp("2025-07-20"))].index)
    assert any("semanas faltando" in x for x in pdd.validate(p, clima(p), fim(p)))
    cheio = painel()
    p2 = cheio[cheio["week_start"] != pd.Timestamp("2025-07-20")]
    assert any("semanas ausentes" in x for x in pdd.validate(p2, clima(cheio), fim(p2)))


def test_detecta_panel_end_incoerente_e_nulos():
    p = painel()
    assert any("PANEL_END incoerente" in x for x in pdd.validate(p, clima(p), "2025-01-05"))
    c = clima(p)
    c.loc[0, "chuva_mm"] = np.nan
    assert any("chuva nula" in x for x in pdd.validate(p, c, fim(p)))
    c = clima(p)
    c["umid_media"] = np.nan
    assert any("umid_media" in x for x in pdd.validate(p, c, fim(p)))
    q = p.copy()
    q.loc[0, "casos"] = np.nan
    assert any("nulos" in x for x in pdd.validate(q, clima(q), fim(q)))


def test_clima_faltando_semanas_do_painel():
    p = painel()
    c = clima(p).iloc[:-2]
    assert any("clima sem linha" in x for x in pdd.validate(p, c, fim(p)))


def test_ingestao_pula_download_se_arquivos_existem(tmp_path, monkeypatch):
    for ano in pdd.RAW_YEARS:
        (tmp_path / f"dengue_{ano}.csv").write_text("a,b\n1,2\n")
    chamadas = []
    monkeypatch.setattr(pdd.subprocess, "run", lambda *a, **k: chamadas.append(a))
    assert "pulado" in pdd.ingest(False, tmp_path) and chamadas == []
    assert "download feito" in pdd.ingest(True, tmp_path) and len(chamadas) == 1
    (tmp_path / "dengue_2020.csv").unlink()
    assert "dengue_2020.csv" in pdd.ingest(False, tmp_path) and len(chamadas) == 2


def test_clima_sem_download_so_se_brutos_existem(tmp_path):
    assert "--sem-download" not in pdd.build_climate(False, tmp_path)
    (tmp_path / "clima").mkdir()
    for nome in ("infodengue_alertcity_2611606.csv", "openmeteo_era5_daily_recife.csv"):
        (tmp_path / "clima" / nome).write_text("x\n")
    assert "--sem-download" in pdd.build_climate(False, tmp_path)
    assert "--sem-download" not in pdd.build_climate(True, tmp_path)


def test_backup_restore_e_manifesto(tmp_path):
    p = painel()
    p.assign(week_start=p["week_start"].dt.strftime("%Y-%m-%d")).to_csv(tmp_path / "panel.csv", index=False)
    c = clima(p)
    c.assign(week_start=c["week_start"].dt.strftime("%Y-%m-%d")).to_csv(tmp_path / "clima_semanal.csv", index=False)
    assert pdd.backup(tmp_path) == ["panel.csv", "clima_semanal.csv"]
    original = (tmp_path / "panel.csv").read_text()
    (tmp_path / "panel.csv").write_text("lixo")
    assert pdd.restore(tmp_path) == ["panel.csv", "clima_semanal.csv"]
    assert (tmp_path / "panel.csv").read_text() == original
    manifesto = pdd.publish(tmp_path)
    assert manifesto["panel.csv"]["linhas"] == len(p) and len(manifesto["panel.csv"]["sha256"]) == 64
    assert json.loads((tmp_path / "manifest.json").read_text())["panel.csv"]["fim"] == fim(p)


def previsoes():
    linhas = []
    for i, (b, rot) in enumerate([("A", "alto"), ("B", "medio"), ("C", "baixo"), ("D", "baixo")]):
        linhas.append({"bairro": b, "week_start": "2025-08-17", "target_week": "2025-08-24",
                       "classe_prevista": {"baixo": 0, "medio": 1, "alto": 2}[rot], "rotulo_previsto": rot,
                       "prob_baixo": 0.2, "prob_medio": 0.3, "prob_alto": 0.5, "risk_score": 80.0 - i, "rank": i + 1})
    return pd.DataFrame(linhas)


def test_previsoes_no_banco_sao_idempotentes():
    eng = create_engine("sqlite://")
    db.init_db(eng)
    assert db.load_latest_predictions(eng).empty
    assert db.save_predictions(eng, previsoes()) == 4
    assert db.save_predictions(eng, previsoes()) == 4
    lidas = db.load_latest_predictions(eng)
    assert len(lidas) == 4 and list(lidas["rank"]) == [1, 2, 3, 4] and str(lidas["week_start"].iloc[0]) == "2025-08-17"
    nova = previsoes().assign(week_start="2025-08-24", target_week="2025-08-31")
    db.save_predictions(eng, nova)
    assert str(db.load_latest_predictions(eng)["week_start"].iloc[0]) == "2025-08-24"


def test_repositorio_prefere_banco_e_cai_para_csv(tmp_path):
    from sqlalchemy.pool import StaticPool

    from api.repository import Repository

    eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    csv = tmp_path / "pred.csv"
    previsoes().assign(risk_score=1.0).to_csv(csv, index=False)
    repo = Repository(panel_path=tmp_path / "panel.csv", predictions_path=csv, engine=eng)
    assert repo.predictions()["risk_score"].iloc[0] == 1.0 and repo.predictions_source == "csv"
    db.save_predictions(eng, previsoes())
    assert repo.predictions()["risk_score"].iloc[0] == 80.0 and repo.predictions_source == "postgres"
    csv.unlink()
    assert repo.predictions_available() is True


def test_monitoramento_resume_classes_e_semana():
    resumo = monitoring.summarize(previsoes())
    m = resumo["metricas"]
    assert resumo["week_start"] == "2025-08-17" and resumo["target_week"] == "2025-08-24"
    assert m["n_bairros"] == 4 and m["n_alto"] == 1 and m["n_medio"] == 1 and m["n_baixo"] == 2
    assert m["frac_baixo"] == pytest.approx(0.5)
