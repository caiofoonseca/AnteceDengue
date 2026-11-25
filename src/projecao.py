"""Projeção sazonal mensal de risco de dengue por bairro (padrão do histórico, NÃO é previsão verificada).

Não existem casos reais de 2026. A projeção repete o padrão sazonal observado nos anos anteriores; ela não
captura surtos nem usa clima futuro, e a magnitude varia muito entre anos epidêmicos (2015-16, 2024).

Regras de método:
  - Mês de uma semana: o mês do domingo de início da semana (week_start). Uma semana dom-sáb que cruza dois
    meses conta inteira para o mês em que começa.
  - Só entram meses completos: todos os domingos do mês precisam existir no painel (o painel termina em
    PANEL_END, então o último mês completo é julho/2025).
  - casos (padronizados) = casos brutos do mês / número de domingos do mês * 52/12. Isso tira o efeito de meses
    com 4 ou 5 semanas; "casos/mês" sempre significa esse valor.
  - Classes (0 baixo, 1 médio, 2 alto): limiares q0.60 e q0.85 (labels.fit_thresholds) calculados sobre os
    valores bairro x mês do TREINO do backtest (ou de todo o histórico real, na projeção final). Os mesmos
    limiares classificam o valor real e o projetado.
  - Todo método só usa anos estritamente anteriores ao ano projetado (ValueError se houver vazamento).
  - Seleção de método: só pelo Backtest A (treino até 2023, projeta 2024). O Backtest B (até 2024, projeta os
    meses disponíveis de 2025) é calculado uma vez e não participa da escolha.
  - Confiança: fração dos anos de histórico em que a classe do mês coincide com a classe projetada
    (alta >= 0,70; média >= 0,45; baixa abaixo disso ou com menos de 3 anos). p25 e p75 são percentis dos
    valores históricos daquele bairro e mês.
"""
import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import f1_score, recall_score

from src import config
from src.labels import apply_thresholds, fit_thresholds

log = logging.getLogger("projecao")

EXPERIMENT = "05-projecao-sazonal"
TARGET_YEAR = 2026
OUTPUT_PATH = config.PROJECTION_PATH
META_PATH = config.PROJECTION_META_PATH
BACKTEST_PATH = config.REPORTS_DIR / "projecao_backtest.json"
REPORT_PATH = config.REPORTS_DIR / "projecao_sazonal.md"
FIGURES_DIR = config.REPORTS_DIR / "figuras"
CSV_COLUMNS = ["bairro", "mes", "casos_esperados", "classe_risco", "p25", "p75", "confianca", "metodo",
               "ultima_data_real_usada"]
BASELINE = "ultimo_ano"
HALF_LIVES = (1, 2, 3)
METHODS = ("climatologia", "ultimo_ano", "recencia_h1", "recencia_h2", "recencia_h3", "random_forest")
CONF_HIGH, CONF_MID, MIN_YEARS = 0.70, 0.45, 3
WEEKS_PER_MONTH = 52 / 12
WARNING_TEMPLATE = ("Projeção sazonal baseada no histórico até {data}; não há dados reais de 2026 para verificação.")


def sundays_in_month(ano: int, mes: int) -> list[pd.Timestamp]:
    dias = pd.date_range(f"{ano}-{mes:02d}-01", periods=pd.Period(f"{ano}-{mes:02d}").days_in_month, freq="D")
    return [d for d in dias if d.weekday() == 6]


def monthly_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Painel semanal (bairro, week_start, casos) -> bairro x mês completo (colunas: bairro, ano, mes, n_semanas,
    casos_brutos, casos). O mês é o do domingo de início; meses incompletos no painel são descartados."""
    p = panel.copy()
    p["week_start"] = pd.to_datetime(p["week_start"])
    primeira, ultima = p["week_start"].min(), p["week_start"].max()
    p["ano"], p["mes"] = p["week_start"].dt.year, p["week_start"].dt.month
    agg = p.groupby(["bairro", "ano", "mes"], as_index=False).agg(n_presentes=("week_start", "nunique"),
                                                                   casos_brutos=("casos", "sum"))
    esperado = {}
    for ano, mes in agg[["ano", "mes"]].drop_duplicates().itertuples(index=False):
        domingos = sundays_in_month(int(ano), int(mes))
        completo = bool(domingos) and domingos[0] >= primeira and domingos[-1] <= ultima
        esperado[(ano, mes)] = (len(domingos), completo)
    agg["n_semanas"] = [esperado[(a, m)][0] for a, m in zip(agg["ano"], agg["mes"])]
    agg["completo"] = [esperado[(a, m)][1] and n == esperado[(a, m)][0]
                       for a, m, n in zip(agg["ano"], agg["mes"], agg["n_presentes"])]
    agg = agg[agg["completo"]].drop(columns=["completo", "n_presentes"])
    agg["casos"] = agg["casos_brutos"] / agg["n_semanas"] * WEEKS_PER_MONTH
    return agg.sort_values(["bairro", "ano", "mes"]).reset_index(drop=True)


def _check_no_leak(history: pd.DataFrame, target_year: int) -> None:
    if (history["ano"] >= target_year).any():
        raise ValueError(f"histórico contém dados de {target_year} ou posteriores: vazamento do período projetado")


def _wide(history: pd.DataFrame) -> pd.DataFrame:
    return history.pivot_table(index=["bairro", "mes"], columns="ano", values="casos")


def _weighted_mean(wide: pd.DataFrame, target_year: int, half_life: float | None) -> pd.Series:
    anos = np.asarray(wide.columns, dtype=float)
    pesos = np.ones_like(anos) if half_life is None else 0.5 ** ((target_year - anos) / half_life)
    valores = wide.to_numpy(dtype=float)
    mascara = ~np.isnan(valores)
    num = np.where(mascara, valores, 0.0) @ pesos
    den = mascara @ pesos
    return pd.Series(np.where(den > 0, num / np.where(den > 0, den, 1), np.nan), index=wide.index)


def _last_value(wide: pd.DataFrame) -> pd.Series:
    valores = wide.to_numpy(dtype=float)
    saida = np.full(len(wide), np.nan)
    for j in range(valores.shape[1]):
        col = valores[:, j]
        saida = np.where(np.isnan(col), saida, col)
    return pd.Series(saida, index=wide.index)


def forecast_climatology(history: pd.DataFrame, target_year: int) -> pd.Series:
    _check_no_leak(history, target_year)
    return _weighted_mean(_wide(history), target_year, None)


def forecast_last_year(history: pd.DataFrame, target_year: int) -> pd.Series:
    _check_no_leak(history, target_year)
    return _last_value(_wide(history))


def forecast_recency(history: pd.DataFrame, target_year: int, half_life: float) -> pd.Series:
    _check_no_leak(history, target_year)
    return _weighted_mean(_wide(history), target_year, half_life)


def _calendar_features(history: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Features de calendário/histórico para (bairro, mes) do ano dado, usando só anos < ano."""
    passado = history[history["ano"] < ano]
    wide = _wide(passado)
    clima = _weighted_mean(wide, ano, None)
    ultimo = _last_value(wide)
    recente = _weighted_mean(wide, ano, 2)
    media_bairro = passado.groupby("bairro")["casos"].mean()
    feats = pd.DataFrame({"clima_mes": clima, "ultimo_ano_mes": ultimo, "recencia_mes": recente}).reset_index()
    feats["media_bairro"] = feats["bairro"].map(media_bairro)
    cidade_mes = passado.groupby(["ano", "mes"])["casos"].sum().groupby("mes").mean()
    feats["indice_sazonal_cidade"] = feats["mes"].map(cidade_mes / cidade_mes.mean())
    ano_anterior = passado[passado["ano"] == passado["ano"].max()]
    meses_ref = ano_anterior["mes"].unique()
    base = passado[(passado["ano"] < passado["ano"].max()) & passado["mes"].isin(meses_ref)]
    por_bairro_ref = ano_anterior.groupby("bairro")["casos"].sum()
    por_bairro_base = base.groupby("bairro")["casos"].sum() / max(base["ano"].nunique(), 1)
    tendencia = (por_bairro_ref + 1.0) / (por_bairro_base.reindex(por_bairro_ref.index) + 1.0)
    feats["tendencia_ano"] = feats["bairro"].map(tendencia).fillna(1.0)
    feats["seno_mes"] = np.sin(2 * np.pi * feats["mes"] / 12)
    feats["cosseno_mes"] = np.cos(2 * np.pi * feats["mes"] / 12)
    return feats


FEATURE_COLUMNS = ["clima_mes", "ultimo_ano_mes", "recencia_mes", "media_bairro", "indice_sazonal_cidade",
                   "tendencia_ano", "seno_mes", "cosseno_mes"]


def forecast_random_forest(history: pd.DataFrame, target_year: int, seed: int = config.SEED) -> pd.Series:
    """RandomForest só com calendário e histórico (sem casos recentes); alvo em log1p. Treina com anos < target_year."""
    _check_no_leak(history, target_year)
    anos = sorted(history["ano"].unique())
    linhas = []
    for ano in anos[1:]:
        feats = _calendar_features(history, ano)
        real = history[history["ano"] == ano][["bairro", "mes", "casos"]]
        linhas.append(feats.merge(real, on=["bairro", "mes"], how="inner"))
    treino = pd.concat(linhas, ignore_index=True)
    treino[FEATURE_COLUMNS] = treino[FEATURE_COLUMNS].fillna(0.0)
    modelo = RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=seed, n_jobs=1)
    modelo.fit(treino[FEATURE_COLUMNS], np.log1p(treino["casos"]))
    alvo = _calendar_features(history, target_year)
    previsto = np.expm1(modelo.predict(alvo[FEATURE_COLUMNS].fillna(0.0)))
    return pd.Series(np.clip(previsto, 0, None), index=pd.MultiIndex.from_frame(alvo[["bairro", "mes"]]))


def forecast(method: str, history: pd.DataFrame, target_year: int) -> pd.Series:
    if method == "climatologia":
        return forecast_climatology(history, target_year)
    if method == "ultimo_ano":
        return forecast_last_year(history, target_year)
    if method.startswith("recencia_h"):
        return forecast_recency(history, target_year, float(method.removeprefix("recencia_h")))
    if method == "random_forest":
        return forecast_random_forest(history, target_year)
    raise ValueError(f"método desconhecido: {method}")


def fit_month_thresholds(history: pd.DataFrame) -> tuple[float, float]:
    return fit_thresholds(history["casos"])


def evaluate(real: pd.DataFrame, previsto: pd.Series, thresholds: tuple[float, float]) -> dict:
    """real: bairro, mes, casos. previsto: Series indexada por (bairro, mes)."""
    junto = real.set_index(["bairro", "mes"])[["casos"]].join(previsto.rename("prev"), how="left")
    junto["prev"] = junto["prev"].fillna(0.0)
    y_real, y_prev = apply_thresholds(junto["casos"], thresholds), apply_thresholds(junto["prev"], thresholds)
    rhos = []
    for _, g in junto.groupby(level="mes"):
        if g["casos"].nunique() > 1 and g["prev"].nunique() > 1:
            rhos.append(spearmanr(g["casos"], g["prev"]).statistic)
    cidade = junto.groupby(level="mes")[["casos", "prev"]].sum()
    tem_alto = bool((y_real == 2).any())
    return {
        "f1_macro": float(f1_score(y_real, y_prev, average="macro", labels=[0, 1, 2], zero_division=0)),
        "recall_alto": float(recall_score(y_real, y_prev, labels=[2], average=None, zero_division=0)[0])
        if tem_alto else float("nan"),
        "spearman_bairros": float(np.mean(rhos)) if rhos else float("nan"),
        "mae_casos_mes": float((junto["casos"] - junto["prev"]).abs().mean()),
        "mae_cidade_casos_mes": float((cidade["casos"] - cidade["prev"]).abs().mean()),
        "pico_real": int(cidade["casos"].idxmax()), "pico_previsto": int(cidade["prev"].idxmax()),
        "pico_acerto": float(cidade["casos"].idxmax() == cidade["prev"].idxmax()),
        "n_linhas": int(len(junto)), "n_meses": int(junto.index.get_level_values("mes").nunique()),
        "limiares": [float(thresholds[0]), float(thresholds[1])],
        "distribuicao_real": {str(c): int((y_real == c).sum()) for c in (0, 1, 2)},
    }


def backtest(monthly: pd.DataFrame, train_end_year: int, target_year: int, methods=METHODS) -> dict:
    """Treina só com anos <= train_end_year e compara com o real de target_year (meses completos disponíveis)."""
    history = monthly[monthly["ano"] <= train_end_year]
    real = monthly[monthly["ano"] == target_year]
    if real.empty:
        raise ValueError(f"sem dados reais de {target_year} para o backtest")
    thresholds = fit_month_thresholds(history)
    return {m: evaluate(real, forecast(m, history, target_year), thresholds) for m in methods}


def choose_method(resultados_a: dict) -> str:
    """Escolhe pelo Backtest A: maior F1-macro entre os candidatos (o baseline não concorre); empate: menor MAE."""
    candidatos = {m: r for m, r in resultados_a.items() if m != BASELINE}
    return min(candidatos, key=lambda m: (-round(candidatos[m]["f1_macro"], 6), candidatos[m]["mae_casos_mes"]))


def confidence(wide: pd.DataFrame, projected: pd.Series, thresholds: tuple[float, float]) -> pd.Series:
    classes_hist = apply_thresholds(wide.to_numpy(dtype=float).ravel(), thresholds).reshape(wide.shape)
    valido = ~np.isnan(wide.to_numpy(dtype=float))
    classe_proj = apply_thresholds(projected.reindex(wide.index).fillna(0).to_numpy(), thresholds)[:, None]
    n = valido.sum(axis=1)
    acordo = ((classes_hist == classe_proj) & valido).sum(axis=1) / np.where(n > 0, n, 1)
    nivel = np.where((acordo >= CONF_HIGH) & (n >= MIN_YEARS), "alta",
                     np.where((acordo >= CONF_MID) & (n >= MIN_YEARS), "media", "baixa"))
    return pd.Series(nivel, index=wide.index)


def project_year(monthly: pd.DataFrame, target_year: int, method: str, last_date: str) -> tuple[pd.DataFrame, tuple]:
    """Projeção final do ano alvo com todo o histórico real (anos < target_year)."""
    history = monthly[monthly["ano"] < target_year]
    thresholds = fit_month_thresholds(history)
    previsto = forecast(method, history, target_year)
    wide = _wide(history)
    p25 = pd.Series(np.nanpercentile(wide.to_numpy(dtype=float), 25, axis=1), index=wide.index)
    p75 = pd.Series(np.nanpercentile(wide.to_numpy(dtype=float), 75, axis=1), index=wide.index)
    conf = confidence(wide, previsto, thresholds)
    out = pd.DataFrame({"casos_esperados": previsto.round(2), "p25": p25.round(2), "p75": p75.round(2),
                        "confianca": conf}).reset_index()
    out["classe_risco"] = apply_thresholds(out["casos_esperados"], thresholds)
    out["mes"] = [f"{target_year}-{m:02d}" for m in out["mes"]]
    out["metodo"] = method
    out["ultima_data_real_usada"] = last_date
    return out.sort_values(["bairro", "mes"]).reset_index(drop=True)[CSV_COLUMNS], thresholds


def warning_text(last_date: str) -> str:
    return WARNING_TEMPLATE.format(data=pd.Timestamp(last_date).strftime("%d/%m/%Y"))


def _clean(obj):
    """NaN vira None para o JSON ser válido."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False, lineterminator="\n")
    tmp.replace(path)


def city_curve(monthly: pd.DataFrame) -> pd.DataFrame:
    """Casos/mês da cidade (soma dos bairros) por ano e mês."""
    return monthly.groupby(["ano", "mes"], as_index=False)["casos"].sum()


def city_summary(monthly: pd.DataFrame, projecao: pd.DataFrame, target_year: int = TARGET_YEAR) -> tuple[list, dict]:
    """Curva da cidade: projetado por mês (soma dos bairros) com p25-p75 dos totais anuais históricos, e o real por ano."""
    cidade = city_curve(monthly)
    wide = cidade.pivot(index="mes", columns="ano", values="casos")
    soma = projecao.assign(m=projecao["mes"].str[-2:].astype(int)).groupby("m")["casos_esperados"].sum()
    curva = [{"mes": f"{target_year}-{m:02d}", "casos_esperados": round(float(soma[m]), 2),
              "p25": round(float(np.nanpercentile(wide.loc[m], 25)), 2),
              "p75": round(float(np.nanpercentile(wide.loc[m], 75)), 2)} for m in range(1, 13)]
    historico = {str(ano): [None if np.isnan(wide.loc[m, ano]) else round(float(wide.loc[m, ano]), 2)
                            for m in range(1, 13)] for ano in wide.columns}
    return curva, historico


def report_markdown(meta: dict) -> str:
    """Relatório em Markdown dos backtests e da projeção (reports/projecao_sazonal.md)."""
    linhas = [
        "# Projeção sazonal mensal de risco de dengue para 2026", "",
        f"> {meta['aviso']} É projeção do padrão sazonal, não previsão verificada nem número exato de casos.", "",
        f"- Método escolhido: **{meta['metodo']}** ({meta['metodo_escolhido_por']}).",
        f"- Último mês completo usado: {meta['ultimo_mes_completo']}; painel até {meta['ultima_data_real_usada']}.",
        f"- Limiares de classe (casos/mês, q0.60 e q0.85 só no histórico real): {meta['limiares_casos_mes'][0]:.2f} e "
        f"{meta['limiares_casos_mes'][1]:.2f}.", "",
        "O baseline é o \"mesmo mês do último ano\". F1-macro e recall da classe alta são sobre as classes mensais "
        "(bairro x mês); Spearman é a média, por mês, da correlação entre o ranking real e o projetado dos bairros; "
        "MAE em casos/mês padronizados por bairro; pico = acerto do mês de maior total da cidade.", "",
        metrics_table(meta),
        "## Dados (verificado em 25/11/2026)", "",
        "- O portal de dados abertos do Recife não tem recurso de 2026 e os arquivos de 2013, 2014 e 2025 têm o mesmo "
        "tamanho dos já baixados: não há dados novos. Painel antes e depois: 2015-01-04 a 2025-08-17 (inalterado).",
        "- 2013 e 2014 não foram incorporados: 1.293 e 374 casos confirmados (2014 termina em julho e 2013 está em "
        "outra escala), o que quebraria a série mensal; a decisão de período 2015 a 2025 continua.",
        "- Os registros brutos de 2025 vão até dezembro, mas a cauda tem classificação atrasada; o painel segue "
        "cortado em PANEL_END.", "",
        "## Limitações", "",
        "- Anos epidêmicos (2015-16, 2024) mudam muito a magnitude; o método captura sazonalidade, não surtos.",
        "- Sem dados climáticos futuros e sem casos recentes de 2026.",
        "- Agosto a dezembro de 2025 não entram (cauda com classificação atrasada, ver reports/cauda_2025.md); esses meses "
        "de 2026 se apoiam em anos anteriores a 2025 e a curva tem um degrau entre julho e agosto.",
        "- O Backtest B tem só 7 meses (jan a jul/2025). Ele foi calculado uma vez e não participou da escolha do método.",
        "- Nenhum resultado do modelo semanal nem o teste final foram alterados.", ""]
    return "\n".join(linhas)


def run_all(panel: pd.DataFrame, mlflow_enabled: bool = True, last_date: str = config.PANEL_END,
            output: Path = OUTPUT_PATH, meta_path: Path = META_PATH, backtest_path: Path = BACKTEST_PATH,
            report_path: Path | None = REPORT_PATH) -> dict:
    monthly = monthly_panel(panel)
    ultimo_ano_completo = int(monthly["ano"].max())
    res_a = backtest(monthly, 2023, 2024)
    metodo = choose_method(res_a)
    res_b = backtest(monthly, 2024, ultimo_ano_completo)
    projecao, limiares = project_year(monthly, TARGET_YEAR, metodo, last_date)
    ultimo_mes = monthly.loc[monthly["ano"] == monthly["ano"].max(), "mes"].max()
    curva, historico = city_summary(monthly, projecao)
    meta = {
        "curva_cidade": curva, "historico_cidade": historico,
        "aviso": warning_text(last_date), "metodo": metodo, "ultima_data_real_usada": last_date,
        "ultimo_mes_completo": f"{ultimo_ano_completo}-{int(ultimo_mes):02d}", "limiares_casos_mes": list(limiares),
        "backtest_a": {"treino_ate": 2023, "projeta": 2024, "metodos": res_a},
        "backtest_b": {"treino_ate": 2024, "projeta": ultimo_ano_completo, "metodos": res_b},
        "metodo_escolhido_por": "Backtest A (F1-macro mensal); o Backtest B não participou da escolha",
    }
    write_csv_atomic(projecao, output)
    Path(meta_path).write_text(json.dumps(_clean(meta), ensure_ascii=False, indent=2), encoding="utf-8")
    Path(backtest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(backtest_path).write_text(json.dumps(_clean({k: meta[k] for k in ("backtest_a", "backtest_b", "metodo")}),
                                              ensure_ascii=False, indent=2), encoding="utf-8")
    if report_path is not None:
        Path(report_path).write_text(report_markdown(meta), encoding="utf-8")
    _log_mlflow(meta, projecao, output, meta_path, mlflow_enabled)
    return meta


def _log_mlflow(meta: dict, projecao: pd.DataFrame, output: Path, meta_path: Path, enabled: bool) -> None:
    from src.tracking import Tracker

    tracker = Tracker(EXPERIMENT, enabled=enabled)
    for rotulo, bloco in (("A", meta["backtest_a"]), ("B", meta["backtest_b"])):
        for metodo, m in bloco["metodos"].items():
            with tracker.run(f"backtest-{rotulo}-{metodo}", tags={"backtest": rotulo, "metodo": metodo}):
                tracker.log_params({"treino_ate": bloco["treino_ate"], "projeta": bloco["projeta"], "metodo": metodo,
                                    "limiares": m["limiares"]})
                tracker.log_metrics({k: v for k, v in m.items() if isinstance(v, float) and not np.isnan(v)})
    with tracker.run("projecao-2026", tags={"metodo": meta["metodo"]}):
        tracker.log_params({"metodo": meta["metodo"], "ultima_data_real_usada": meta["ultima_data_real_usada"],
                            "escolha": meta["metodo_escolhido_por"]})
        tracker.log_metrics({"linhas": len(projecao)})
        tracker.log_artifact(Path(output))
        tracker.log_artifact(Path(meta_path))


def metrics_table(meta: dict) -> str:
    colunas = ["f1_macro", "recall_alto", "spearman_bairros", "mae_casos_mes", "pico_acerto"]
    linhas = []
    for rotulo, chave in (("A (até 2023 -> 2024)", "backtest_a"), ("B (até 2024 -> 2025)", "backtest_b")):
        linhas += [f"### Backtest {rotulo}", "", "| método | " + " | ".join(colunas) + " |",
                   "|---|" + "---|" * len(colunas)]
        for metodo, m in meta[chave]["metodos"].items():
            nome = f"{metodo} (baseline)" if metodo == BASELINE else metodo
            linhas.append(f"| {nome} | " + " | ".join("n/a" if np.isnan(m[c]) else f"{m[c]:.3f}" for c in colunas) + " |")
        linhas.append("")
    return "\n".join(linhas)


def main(argv=None) -> dict:
    parser = argparse.ArgumentParser(description="Projeção sazonal mensal 2026 (backtests, CSV e metadados)")
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    meta = run_all(panel, mlflow_enabled=not args.no_mlflow)
    print(f"método escolhido (Backtest A): {meta['metodo']}")
    print(metrics_table(meta))
    return meta


if __name__ == "__main__":
    main()
