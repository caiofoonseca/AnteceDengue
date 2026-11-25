"""Transformações de dados do dashboard (sem Streamlit), para poderem ser testadas com pytest.

O dashboard fala em "índice de risco" (0 a 100, não calibrado), nunca em probabilidade de surto.
"""
import json
from pathlib import Path

import pandas as pd

CLASSES = ["baixo", "medio", "alto"]
CLASS_TEXT = {"baixo": "Baixo", "medio": "Médio", "alto": "Alto"}
COLOR_SCALE = "Oranges"
RISK_RANGE = (0, 100)
GEOJSON_PATH = Path(__file__).resolve().parent / "assets" / "bairros.geojson"
SENSOR_TEST_SOURCES = ("simulado", "simulador", "teste", "sintetico", "sintético")
SENSOR_API_SOURCES = ("open-meteo", "openmeteo", "api")


def format_date(valor) -> str:
    """'2025-08-17' -> '17/08/2025'."""
    return pd.to_datetime(valor).strftime("%d/%m/%Y")


def weeks_notice(week_start, target_week) -> str:
    return (f"Semana base: {format_date(week_start)} | semana prevista: {format_date(target_week)}. "
            "O índice de risco é uma previsão para a semana seguinte à última semana dos dados; "
            "não é monitoramento em tempo real nem diagnóstico.")


def load_geojson(path: Path = GEOJSON_PATH) -> dict | None:
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def predictions_frame(payload: dict) -> pd.DataFrame:
    """Previsões da API em um DataFrame com nomes de coluna em português, ordenado por rank."""
    df = pd.DataFrame(payload["predictions"])
    if df.empty:
        return pd.DataFrame(columns=["bairro", "classe", "indice", "rank", "prob_baixo", "prob_medio", "prob_alto"])
    out = pd.DataFrame({
        "bairro": df["bairro"], "classe": df["rotulo_previsto"].map(CLASS_TEXT), "indice": df["risk_score"],
        "rank": df["rank"], "prob_baixo": df["prob_baixo"], "prob_medio": df["prob_medio"],
        "prob_alto": df["prob_alto"]})
    return out.sort_values("rank").reset_index(drop=True)


def geojson_coverage(geojson: dict, frame: pd.DataFrame) -> dict:
    """Bairros do mapa sem previsão e bairros com previsão sem polígono."""
    no_mapa = {f["properties"]["bairro"] for f in geojson["features"]}
    com_previsao = set(frame["bairro"])
    return {"sem_previsao": sorted(no_mapa - com_previsao), "sem_poligono": sorted(com_previsao - no_mapa),
            "casados": len(no_mapa & com_previsao)}


def map_ready(geojson: dict | None, frame: pd.DataFrame) -> bool:
    """O mapa só é desenhado se o GeoJSON existe e cobre todos os bairros com previsão."""
    if geojson is None or frame.empty:
        return False
    return not geojson_coverage(geojson, frame)["sem_poligono"]


def class_counts(frame: pd.DataFrame) -> dict[str, int]:
    contagem = frame["classe"].value_counts()
    return {CLASS_TEXT[c]: int(contagem.get(CLASS_TEXT[c], 0)) for c in CLASSES}


def ranking_table(frame: pd.DataFrame, top: int, classes: list[str] | None = None) -> pd.DataFrame:
    """N bairros de maior índice, opcionalmente só de certas classes (textos como 'Alto')."""
    df = frame
    if classes:
        df = df[df["classe"].isin(classes)]
    df = df.sort_values("rank").head(top)
    return df.rename(columns={"rank": "posição", "bairro": "bairro", "classe": "classe", "indice": "índice de risco"})[
        ["posição", "bairro", "classe", "índice de risco"]].reset_index(drop=True)


def ranking_labels(table: pd.DataFrame) -> pd.Series:
    """Rótulo do gráfico: a classe aparece em texto, não só na cor."""
    return table["bairro"] + " (" + table["classe"] + ")"


def probabilities_frame(item: dict) -> pd.DataFrame:
    return pd.DataFrame({
        "classe": [CLASS_TEXT[c] for c in CLASSES],
        "probabilidade (%)": [100 * item["prob_baixo"], 100 * item["prob_medio"], 100 * item["prob_alto"]]})


def cases_frame(detail: dict) -> pd.DataFrame:
    df = pd.DataFrame(detail["casos_semanais"])
    if df.empty:
        return pd.DataFrame({"semana": pd.to_datetime([]), "casos": []})
    return pd.DataFrame({"semana": pd.to_datetime(df["week_start"]), "casos": df["casos"]})


def sensor_frame(items: list[dict]) -> pd.DataFrame:
    colunas = ["bairro", "semana", "temperatura (°C)", "umidade (%)", "chuva (mm)", "leituras", "bateria mínima (V)"]
    if not items:
        return pd.DataFrame(columns=colunas)
    df = pd.DataFrame(items)
    return pd.DataFrame({
        "bairro": df["bairro"], "semana": pd.to_datetime(df["week_start"]), "temperatura (°C)": df["temp_media"],
        "umidade (%)": df["umid_media"], "chuva (mm)": df["chuva_mm"], "leituras": df["n_leituras"],
        "bateria mínima (V)": df["bateria_min"]}).sort_values(["bairro", "semana"]).reset_index(drop=True)


def sensor_status(frame: pd.DataFrame) -> pd.DataFrame:
    """Por bairro com leituras: última semana, leituras nessa semana, total e menor bateria."""
    if frame.empty:
        return pd.DataFrame(columns=["bairro", "última semana", "leituras na última semana", "semanas com dados",
                                     "bateria mínima (V)"])
    linhas = []
    for bairro, g in frame.groupby("bairro"):
        ultima = g.sort_values("semana").iloc[-1]
        linhas.append({"bairro": bairro, "última semana": format_date(ultima["semana"]),
                       "leituras na última semana": int(ultima["leituras"]), "semanas com dados": len(g),
                       "bateria mínima (V)": g["bateria mínima (V)"].min()})
    return pd.DataFrame(linhas)


def sensor_is_test(source: str | None) -> bool:
    return (source or "").strip().lower() in SENSOR_TEST_SOURCES


def sensor_is_open_meteo(source: str | None) -> bool:
    return (source or "").strip().lower() in SENSOR_API_SOURCES


def model_comparison_table(info: dict) -> pd.DataFrame:
    """RandomForest x persistência na validação e no teste (F1-macro e recall da classe alto)."""
    val, teste = info["validation_metrics"], info["test_metrics"]

    def fmt(v):
        return "—" if v is None else f"{v:.3f}"

    return pd.DataFrame([
        {"métrica": "F1-macro", "RandomForest (validação)": fmt(val.get("f1_macro")),
         "Persistência (validação)": fmt(val.get("persistencia_f1_macro")),
         "RandomForest (teste)": fmt(teste.get("f1_macro")), "Persistência (teste)": fmt(teste.get("persistencia_f1_macro"))},
        {"métrica": "Recall da classe alto", "RandomForest (validação)": fmt(val.get("recall_alto")),
         "Persistência (validação)": fmt(val.get("persistencia_recall_alto")),
         "RandomForest (teste)": fmt(teste.get("recall_alto")),
         "Persistência (teste)": fmt(teste.get("persistencia_recall_alto"))},
        {"métrica": "AUC macro (one-vs-rest)", "RandomForest (validação)": fmt(val.get("auc_macro")),
         "Persistência (validação)": "—", "RandomForest (teste)": fmt(teste.get("auc_macro")),
         "Persistência (teste)": "—"},
    ])


def difference_sentence(info: dict) -> str:
    teste = info["test_metrics"]
    inf, sup = teste["f1_diff_ic95"]
    dif = teste["f1_macro"] - teste["persistencia_f1_macro"]
    exclui_zero = inf > 0 or sup < 0
    leitura = ("O intervalo não inclui zero, mas a vantagem é pequena e vem de uma janela de só 26 semanas."
               if exclui_zero else "O intervalo inclui zero: não há evidência estatística de que o modelo supere a persistência.")
    return (f"No teste, a diferença de F1-macro entre o RandomForest e a persistência é {dif:+.3f}, com intervalo de "
            f"confiança de 95% (bootstrap por blocos de semanas) de [{inf:+.3f}, {sup:+.3f}]. {leitura}")


LIMITATIONS = [
    "O teste tem só 26 semanas (uma estação): o intervalo de confiança mede a incerteza dessa janela, não a "
    "variação entre épocas do ano.",
    "As probabilidades do modelo não são calibradas; o índice de risco serve para ordenar bairros, não para "
    "estimar chances.",
    "O clima tem pouco sinal: na importância por permutação, temperatura, umidade e chuva ficaram em torno de zero.",
    "O modelo depende dos casos recentes do próprio bairro (médias móveis, caso atual e média histórica); se os "
    "casos chegam com atraso, a previsão também atrasa.",
    "A previsão vale para a semana seguinte à última semana dos dados, não para a semana atual do calendário.",
    "As leituras da estação simulada (API Open-Meteo via MQTT) são exibidas, mas não alimentam o modelo.",
]


def normalize_text(texto: str) -> str:
    """Minúsculas e sem acentos, para a busca por nome de bairro."""
    import unicodedata

    base = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in base if not unicodedata.combining(c)).casefold().strip()


def filter_by_name(table: pd.DataFrame, query: str | None) -> pd.DataFrame:
    """Mantém as linhas cujo bairro contém o texto buscado (sem diferença de maiúsculas e acentos)."""
    if not query or not query.strip():
        return table
    alvo = normalize_text(query)
    return table[table["bairro"].map(normalize_text).str.contains(alvo, regex=False)].reset_index(drop=True)


def comparison_long(info: dict) -> pd.DataFrame:
    """RandomForest x persistência em formato longo (para o gráfico): métrica, conjunto, modelo, valor."""
    linhas = []
    for conjunto, chave in (("Validação", "validation_metrics"), ("Teste", "test_metrics")):
        metricas = info[chave]
        for nome, campo, campo_pers in (("F1-macro", "f1_macro", "persistencia_f1_macro"),
                                        ("Recall da classe alto", "recall_alto", "persistencia_recall_alto")):
            for modelo, valor in (("RandomForest", metricas.get(campo)), ("Persistência", metricas.get(campo_pers))):
                if valor is not None:
                    linhas.append({"métrica": nome, "conjunto": conjunto, "modelo": modelo, "valor": float(valor)})
    return pd.DataFrame(linhas, columns=["métrica", "conjunto", "modelo", "valor"])


MONTH_NAMES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
               "novembro", "dezembro"]
CONFIDENCE_TEXT = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}


def month_label(mes: str) -> str:
    """'2026-07' -> 'Julho de 2026'."""
    ano, numero = mes.split("-")
    return f"{MONTH_NAMES[int(numero) - 1].capitalize()} de {ano}"


def projection_frame(payload: dict) -> pd.DataFrame:
    """Itens de /projecao/2026 em DataFrame: bairro, mes, casos, classe (texto), p25, p75, confianca."""
    colunas = ["bairro", "mes", "casos", "classe", "p25", "p75", "confianca"]
    itens = payload.get("items", [])
    if not itens:
        return pd.DataFrame(columns=colunas)
    df = pd.DataFrame(itens)
    return pd.DataFrame({
        "bairro": df["bairro"], "mes": df["mes"], "casos": df["casos_esperados"].astype(float),
        "classe": df["classe_risco"].map(lambda c: CLASSES[int(c)]), "p25": df["p25"].astype(float),
        "p75": df["p75"].astype(float), "confianca": df["confianca"]})


def projection_months(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["mes"].unique())


def peak_month(payload: dict) -> str | None:
    """Mês de maior projeção na curva da cidade."""
    curva = payload.get("curva_cidade") or []
    return max(curva, key=lambda c: c["casos_esperados"])["mes"] if curva else None


def projection_ranking(frame: pd.DataFrame, mes: str, top: int = 10) -> pd.DataFrame:
    """Ranking de um mês por casos esperados (bairro, casos/mês, faixa p25 a p75, classe, confiança)."""
    recorte = frame[frame["mes"] == mes].sort_values(["casos", "bairro"], ascending=[False, True]).head(top)
    saida = pd.DataFrame({
        "bairro": recorte["bairro"].to_numpy(), "casos esperados/mês": recorte["casos"].round(1).to_numpy(),
        "p25 a p75 histórico": [f"{a:.1f} a {b:.1f}" for a, b in zip(recorte["p25"], recorte["p75"])],
        "classe": recorte["classe"].map(CLASS_TEXT).to_numpy(),
        "confiança": recorte["confianca"].map(CONFIDENCE_TEXT).to_numpy()})
    return saida.reset_index(drop=True)


def projection_curve(payload: dict) -> pd.DataFrame:
    """Curva sazonal da cidade: mes (1 a 12), casos_esperados, p25, p75."""
    df = pd.DataFrame(payload.get("curva_cidade", []))
    if df.empty:
        return pd.DataFrame(columns=["mes", "casos_esperados", "p25", "p75"])
    df["mes"] = df["mes"].str[-2:].astype(int)
    return df


def projection_history(payload: dict) -> dict[str, list]:
    return payload.get("historico_cidade", {})


def _peak_text(m: dict) -> str:
    if m.get("pico_acerto") == 1.0:
        return "acertou"
    return f"errou (real {m['pico_real']}, projetado {m['pico_previsto']})"


def backtest_rows(backtest_b: dict) -> pd.DataFrame:
    """Métricas do Backtest B: método escolhido ao lado do baseline 'mesmo mês do último ano'."""
    def valor(m, chave, casas):
        v = m.get(chave)
        return "n/d" if v is None else f"{v:.{casas}f}"

    linhas = [("F1-macro das classes mensais", "f1_macro", 3), ("Recall da classe alta", "recall_alto", 3),
              ("Spearman do ranking de bairros (média dos meses)", "spearman_bairros", 3),
              ("Erro médio absoluto (casos/mês por bairro)", "mae_casos_mes", 2)]
    escolhido, base = backtest_b["escolhido"], backtest_b["baseline_mesmo_mes_ultimo_ano"]
    tabela = [{"métrica": nome, "método escolhido": valor(escolhido, chave, casas),
               "baseline (mesmo mês do último ano)": valor(base, chave, casas)} for nome, chave, casas in linhas]
    tabela.append({"métrica": "Mês de pico da cidade", "método escolhido": _peak_text(escolhido),
                   "baseline (mesmo mês do último ano)": _peak_text(base)})
    return pd.DataFrame(tabela)
