"""Dashboard Streamlit do AnteceDengue. Consome só a API (API_URL, padrão http://localhost:8000).

Uso: streamlit run app/dashboard.py
O dashboard fala sempre em "índice de risco" (0 a 100, não calibrado). Não é monitoramento em tempo real
nem diagnóstico. As leituras do sensor são exibidas como monitoramento de microclima e não alimentam o modelo.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from app import data, ui
from app.api_client import ApiClient, ApiError, ApiUnavailable, api_url

st.set_page_config(page_title="AnteceDengue — índice de risco de dengue", page_icon="🦟", layout="wide")


@st.cache_data(ttl=60, show_spinner=False)
def fetch(base_url: str, path: str, params: tuple = ()):
    return ApiClient(base_url).get(path, dict(params) or None)


def get(path: str, **params):
    return fetch(api_url(), path, tuple(sorted((k, v) for k, v in params.items() if v is not None)))


def show_api_down(erro: ApiUnavailable) -> None:
    ui.render(ui.hero(simulated=ui.simulated_source()))
    st.error(f"Não consegui falar com a API em **{erro.base_url}** ({erro.motivo}).")
    st.markdown(
        "Suba a API com `uvicorn api.main:app` ou ajuste a variável de ambiente `API_URL` com o endereço certo, "
        "e recarregue esta página.")
    st.stop()


def weeks_banner(pred: dict | None) -> None:
    if pred and pred.get("week_start"):
        st.info(data.weeks_notice(pred["week_start"], pred["target_week"]), icon="🗓️")
    else:
        st.warning("Sem previsões disponíveis. Gere-as com `python -m src.predict_batch`.")


def tab_map(frame: pd.DataFrame, pred: dict) -> None:
    st.subheader("Mapa do índice de risco por bairro")
    weeks_banner(pred)
    if frame.empty:
        return
    contagem = data.class_counts(frame)
    cols = st.columns(3)
    for col, (nome, n) in zip(cols, contagem.items()):
        col.metric(f"Bairros com classe {nome}", n)
    geojson = data.load_geojson()
    if data.map_ready(geojson, frame):
        figura = px.choropleth_map(
            frame, geojson=geojson, locations="bairro", featureidkey="properties.bairro", color="indice",
            color_continuous_scale=data.COLOR_SCALE, range_color=data.RISK_RANGE, hover_name="bairro",
            hover_data={"classe": True, "indice": ":.1f", "rank": True, "bairro": False},
            labels={"indice": "Índice de risco (0–100)", "classe": "Classe", "rank": "Posição"},
            map_style="carto-positron", center={"lat": -8.05, "lon": -34.92}, zoom=10.6, opacity=0.8, height=620)
        figura.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0},
                             coloraxis_colorbar={"title": "Índice de risco<br>(0–100, não calibrado)"})
        st.plotly_chart(figura, width="stretch")
        st.caption("Cor: índice de risco (0 = menor, 100 = maior; uma só matiz, legível por daltônicos). "
                   "A classe de cada bairro aparece em texto ao passar o mouse e no ranking abaixo.")
    else:
        st.warning("Os limites geográficos dos bairros (app/assets/bairros.geojson) não estão disponíveis ou não "
                   "cobrem todos os bairros. Mostrando o ranking em barras no lugar do mapa.")
        tabela = data.ranking_table(frame, len(frame))
        figura = px.bar(tabela, x="índice de risco", y=data.ranking_labels(tabela), orientation="h",
                        color="índice de risco", color_continuous_scale=data.COLOR_SCALE, range_color=data.RISK_RANGE,
                        labels={"y": "Bairro (classe)", "índice de risco": "Índice de risco (0–100)"}, height=1500)
        figura.update_yaxes(autorange="reversed")
        st.plotly_chart(figura, width="stretch")
    st.markdown("**10 bairros de maior índice**")
    st.dataframe(data.ranking_table(frame, 10), hide_index=True, width="stretch")


def tab_ranking(frame: pd.DataFrame, pred: dict) -> None:
    st.subheader("Ranking de bairros por índice de risco")
    weeks_banner(pred)
    if frame.empty:
        return
    esquerda, direita = st.columns([1, 2])
    with esquerda:
        n = st.slider("Quantos bairros mostrar", 5, len(frame), min(15, len(frame)), key="rank_n")
        classes = st.multiselect("Filtrar por classe", list(data.CLASS_TEXT.values()),
                                 default=list(data.CLASS_TEXT.values()), key="rank_classes")
    tabela = data.ranking_table(frame, n, classes)
    if tabela.empty:
        st.info("Nenhum bairro nas classes selecionadas.")
        return
    with esquerda:
        st.dataframe(tabela, hide_index=True, width="stretch", height=480)
    with direita:
        figura = px.bar(tabela, x="índice de risco", y=data.ranking_labels(tabela), orientation="h",
                        color="índice de risco", color_continuous_scale=data.COLOR_SCALE, range_color=data.RISK_RANGE,
                        labels={"y": "Bairro (classe)", "índice de risco": "Índice de risco (0–100)"},
                        title=f"{len(tabela)} bairros de maior índice de risco", height=max(380, 26 * len(tabela)))
        figura.update_yaxes(autorange="reversed")
        st.plotly_chart(figura, width="stretch")
    st.caption("O índice (50 x prob. médio + 100 x prob. alto) ordena os bairros entre si; não é probabilidade de "
               "surto e não é calibrado.")


def tab_bairro(pred: dict) -> None:
    st.subheader("Detalhe de um bairro")
    weeks_banner(pred)
    lista = get("/bairros")["bairros"]
    padrao = lista.index("BOA VIAGEM") if "BOA VIAGEM" in lista else 0
    escolhido = st.selectbox("Bairro", lista, index=padrao, key="bairro_sel")
    try:
        detalhe = get(f"/bairros/{escolhido}")
    except ApiError as erro:
        st.error(erro.detail)
        return
    previsao = detalhe["previsao"]
    if previsao:
        c1, c2, c3 = st.columns(3)
        c1.metric("Classe prevista", data.CLASS_TEXT[previsao["rotulo_previsto"]])
        c2.metric("Índice de risco (0–100)", f"{previsao['risk_score']:.1f}")
        c3.metric("Posição no ranking", f"{previsao['rank']}º de {len(lista)}")
        probs = data.probabilities_frame(previsao)
        figura = px.bar(probs, x="probabilidade (%)", y="classe", orientation="h", text="probabilidade (%)",
                        color="probabilidade (%)", color_continuous_scale=data.COLOR_SCALE, range_color=(0, 100),
                        title="Probabilidade estimada por classe (semana prevista)", height=260)
        figura.update_traces(texttemplate="%{text:.1f}%")
        figura.update_layout(coloraxis_showscale=False, xaxis_range=[0, 100])
        st.plotly_chart(figura, width="stretch")
        st.caption("Atenção: as probabilidades do modelo não são calibradas. Use-as como ordem de grandeza, não "
                   "como chance real.")
    else:
        st.warning(detalhe.get("nota") or "Sem previsão para este bairro.")
    casos = data.cases_frame(detalhe)
    if not casos.empty:
        figura = px.bar(casos, x="semana", y="casos", title="Casos confirmados por semana (últimas 26 semanas)",
                        labels={"semana": "Semana (início no domingo)", "casos": "Casos confirmados por semana"},
                        height=340)
        figura.update_traces(marker_color="#b45309")
        st.plotly_chart(figura, width="stretch")
        st.caption("Casos do painel do portal de dados abertos (chegam com atraso). Os casos recentes alimentam a previsão.")
    sensor = data.sensor_frame(detalhe["sensor_semanal"])
    if not sensor.empty:
        st.markdown("**Microclima medido pelo sensor neste bairro** (não alimenta o modelo)")
        st.dataframe(sensor.drop(columns="bairro").assign(semana=sensor["semana"].dt.strftime("%d/%m/%Y")),
                     hide_index=True, width="stretch")


def tab_sensor() -> None:
    st.subheader("Sensor: monitoramento de microclima")
    st.info("As leituras do sensor são exibidas aqui como monitoramento de microclima. **Elas não alimentam o "
            "modelo de risco**: o modelo usa só casos e clima de reanálise.", icon="📡")
    fonte = os.getenv("SENSOR_FONTE", "real")
    if data.sensor_is_test(fonte):
        st.warning(f"As leituras mostradas vêm de dados **{fonte}** (simulados ou de teste), não de estações reais. "
                   "Defina SENSOR_FONTE=real quando houver estações reais enviando dados.", icon="🧪")
    try:
        itens = get("/sensor/weekly")["items"]
    except ApiError as erro:
        st.warning(f"Banco do sensor indisponível: {erro.detail}")
        return
    frame = data.sensor_frame(itens)
    if frame.empty:
        st.info("As estações ainda não enviaram leituras. Quando o ingestor MQTT gravar leituras válidas e a "
                "agregação semanal rodar, as séries aparecem aqui.")
        return
    st.markdown("**Estado das estações (por bairro)**")
    st.dataframe(data.sensor_status(frame), hide_index=True, width="stretch")
    bairros = st.multiselect("Bairros", sorted(frame["bairro"].unique()), default=sorted(frame["bairro"].unique()),
                             key="sensor_bairros")
    recorte = frame[frame["bairro"].isin(bairros)]
    for coluna, titulo in (("temperatura (°C)", "Temperatura média semanal"), ("umidade (%)", "Umidade relativa média semanal"),
                           ("chuva (mm)", "Chuva total semanal")):
        figura = (px.bar if coluna.startswith("chuva") else px.line)(
            recorte, x="semana", y=coluna, color="bairro", title=titulo,
            labels={"semana": "Semana (início no domingo)", coluna: coluna.capitalize()}, height=300)
        st.plotly_chart(figura, width="stretch")


def tab_modelo(info: dict) -> None:
    st.subheader("Modelo")
    c1, c2, c3 = st.columns(3)
    c1.metric("Modelo", info["name"])
    c2.metric("Versão no Registry", f"{info['version']} ({info['alias']})" if info["version"] else "arquivo local")
    c3.metric("Features", len(info["features"]))
    periodo = info["train_period"]
    st.write(f"Treino (treino + validação): {data.format_date(periodo['inicio'])} a {data.format_date(periodo['fim'])}. "
             f"Limiares de classe (casos por semana no bairro): baixo ≤ {info['thresholds'][0]:g}, médio ≤ "
             f"{info['thresholds'][1]:g}, alto acima disso. scikit-learn {info['sklearn_version_treino']}.")
    with st.expander("Lista de features"):
        st.write(", ".join(info["features"]))
    st.markdown("**RandomForest versus persistência** (persistência = repetir a classe da semana atual)")
    st.dataframe(data.model_comparison_table(info), hide_index=True, width="stretch")
    st.write(data.difference_sentence(info))
    st.caption("Validação e teste têm distribuições de classe diferentes e não são comparáveis entre si.")
    st.warning("**Limitações**\n\n" + "\n".join(f"- {t}" for t in data.LIMITATIONS))


def main() -> None:
    ui.load_css()
    try:
        get("/health")
        info = get("/model")
    except ApiUnavailable as erro:
        show_api_down(erro)
        return
    aviso = None
    try:
        pred = get("/predictions/latest")
        frame = data.predictions_frame(pred)
    except ApiError as erro:
        pred, frame, aviso = None, data.predictions_frame({"predictions": []}), erro.detail
    semanas = (pred["week_start"], pred["target_week"]) if pred else (None, None)
    ui.render(ui.hero(*semanas, simulated=ui.simulated_source()))
    if aviso:
        st.warning(aviso)
    if pred and not frame.empty:
        ui.render(ui.summary_cards(frame, *semanas))
    abas = st.tabs(["Mapa de risco", "Ranking", "Bairro", "Sensor", "Modelo"])
    try:
        with abas[0]:
            tab_map(frame, pred or {})
        with abas[1]:
            tab_ranking(frame, pred or {})
        with abas[2]:
            tab_bairro(pred or {})
        with abas[3]:
            tab_sensor()
        with abas[4]:
            tab_modelo(info)
    except ApiUnavailable as erro:
        show_api_down(erro)


main()
