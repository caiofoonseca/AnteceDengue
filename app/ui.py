"""Componentes visuais do dashboard (cabeçalho, selos, cartões). Só estilo: nenhum dado é calculado aqui.

O HTML é montado sem quebras de linha nem recuo, porque o Markdown do Streamlit trataria linhas indentadas
como bloco de código. Todo texto que vem da API passa por html.escape.
"""
import html
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app import data

ASSETS = Path(__file__).resolve().parent / "assets"
CSS_PATH = ASSETS / "style.css"
TAGLINE = "Onde o risco de dengue deve estar na próxima semana, bairro a bairro, no Recife"


def load_css(path: Path = CSS_PATH) -> None:
    st.markdown(f"<style>{Path(path).read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render(fragment: str) -> None:
    st.markdown(fragment, unsafe_allow_html=True)


def fmt_num(valor, casas: int = 1) -> str:
    """Número com vírgula decimal (padrão brasileiro): 73.44 -> '73,4'."""
    return f"{float(valor):.{casas}f}".replace(".", ",")


def esc(texto) -> str:
    return html.escape(str(texto), quote=True)


def badge(texto: str, tipo: str = "accent") -> str:
    return f'<span class="badge badge-{esc(tipo)}">{esc(texto)}</span>'


def simulated_source() -> bool:
    return data.sensor_is_test(os.getenv("SENSOR_FONTE", "real"))


def hero(week_start=None, target_week=None, simulated: bool = False) -> str:
    selos = []
    if week_start and target_week:
        selos.append(badge(f"Previsão para a semana de {data.format_date(target_week)}", "accent"))
        selos.append(badge(f"Semana base: {data.format_date(week_start)}", "neutral"))
    if simulated:
        selos.append(badge("Dados simulados", "warn"))
    return ('<header class="hero"><div class="hero-brand"><div class="hero-logo" aria-hidden="true">A</div>'
            f'<div><div class="hero-title">AnteceDengue</div><div class="hero-tagline">{esc(TAGLINE)}</div></div></div>'
            f'<div class="hero-badges">{"".join(selos)}</div></header>')


def kpi_card(rotulo: str, valor: str, dica: str = "", tom: str = "accent", texto: bool = False) -> str:
    classe_valor = "kpi-value kpi-value-text" if texto else "kpi-value"
    dica_html = f'<div class="kpi-hint">{esc(dica)}</div>' if dica else ""
    return (f'<div class="kpi kpi-{esc(tom)}"><div class="kpi-label">{esc(rotulo)}</div>'
            f'<div class="{classe_valor}">{esc(valor)}</div>{dica_html}</div>')


def kpi_grid(cartoes: list[str]) -> str:
    return f'<div class="kpi-grid">{"".join(cartoes)}</div>'


def summary_cards(frame: pd.DataFrame, week_start, target_week) -> str:
    """Cartões do topo: bairros por classe, bairro de maior índice e semana prevista."""
    contagem = data.class_counts(frame)
    total = len(frame)
    primeiro = frame.sort_values("rank").iloc[0]
    return kpi_grid([
        kpi_card("Bairros em risco Alto", str(contagem["Alto"]), f"de {total} bairros", "alto"),
        kpi_card("Bairros em risco Médio", str(contagem["Médio"]), f"de {total} bairros", "medio"),
        kpi_card("Bairros em risco Baixo", str(contagem["Baixo"]), f"de {total} bairros", "baixo"),
        kpi_card("Maior índice de risco", str(primeiro["bairro"]), f"índice {fmt_num(primeiro['indice'])} (0 a 100)",
                 "accent", texto=True),
        kpi_card("Semana prevista", data.format_date(target_week), f"base em {data.format_date(week_start)}",
                 "accent", texto=True),
    ])


FONT_STACK = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
RISK_SCALE = ["#fde8c8", "#f9b872", "#ee8a3b", "#d2561c", "#8a2c08"]
GRID = "#ece8dd"
INK = "#1f2933"
CLASS_SYMBOL = {"Alto": "▲", "Médio": "●", "Baixo": "▼"}
CLASS_KEY = {"Alto": "alto", "Médio": "medio", "Baixo": "baixo"}
CLASS_INK = {"Alto": "#8a2c08", "Médio": "#7a4d00", "Baixo": "#0b5249"}


def class_label(classe: str) -> str:
    """A classe sempre em texto, com um símbolo de apoio: '▲ Alto'."""
    return f"{CLASS_SYMBOL.get(classe, '')} {classe}".strip()


def class_chip(classe: str) -> str:
    return f'<span class="chip chip-{CLASS_KEY.get(classe, "baixo")}">{esc(class_label(classe))}</span>'


def risk_color(indice: float) -> str:
    """Cor da escala de risco (uma só matiz quente, de claro a escuro) para um índice de 0 a 100."""
    pos = min(max(float(indice), 0.0), 100.0) / 100 * (len(RISK_SCALE) - 1)
    i = min(int(pos), len(RISK_SCALE) - 2)
    frac = pos - i
    a, b = RISK_SCALE[i], RISK_SCALE[i + 1]
    canais = [round(int(a[k:k + 2], 16) * (1 - frac) + int(b[k:k + 2], 16) * frac) for k in (1, 3, 5)]
    return "#" + "".join(f"{c:02x}" for c in canais)


def card_title(titulo: str, subtitulo: str = "") -> str:
    sub = f'<div class="card-sub">{esc(subtitulo)}</div>' if subtitulo else ""
    return f'<div class="card-title">{esc(titulo)}</div>{sub}'


def top_panel(frame: pd.DataFrame, n: int = 5) -> str:
    """Painel 'Top N bairros' com uma barra proporcional ao índice de risco."""
    linhas = []
    for _, r in frame.sort_values("rank").head(n).iterrows():
        largura = min(max(float(r["indice"]), 0.0), 100.0)
        linhas.append(
            f'<li class="top-item"><div class="top-head"><span class="top-rank">{int(r["rank"])}</span>'
            f'<span class="top-name">{esc(r["bairro"])}</span><span class="top-value">{fmt_num(r["indice"])}</span></div>'
            f'<div class="bar"><div class="bar-fill" style="width:{largura:.1f}%;background:{risk_color(r["indice"])}"></div></div>'
            f'<div class="top-class">{class_chip(r["classe"])}</div></li>')
    return (card_title(f"Top {n} bairros", "por índice de risco (0 a 100, não calibrado)")
            + f'<ol class="top-list">{"".join(linhas)}</ol>')


def style_figure(fig, height: int | None = None, titulo: str | None = None):
    """Estilo comum dos gráficos: fundo transparente, grades suaves, sem bordas pesadas, fonte do sistema."""
    fig.update_layout(
        font={"family": FONT_STACK, "size": 14, "color": INK}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 16, "t": 56 if titulo else 16, "b": 8}, hoverlabel={"bgcolor": "#ffffff", "font_size": 14,
                                                                                  "font_family": FONT_STACK},
        legend={"orientation": "h", "y": 1.02, "x": 1, "xanchor": "right", "yanchor": "bottom", "title": None})
    if titulo:
        fig.update_layout(title={"text": titulo, "x": 0, "font": {"size": 16, "color": INK}})
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor="rgba(0,0,0,0)", title_font={"size": 13})
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor="rgba(0,0,0,0)", title_font={"size": 13})
    return fig


def ranking_view(table: pd.DataFrame) -> pd.DataFrame:
    """Tabela do ranking para exibição: posição, bairro, classe em texto e índice numérico (para a barra)."""
    return pd.DataFrame({
        "Posição": table["posição"], "Bairro": table["bairro"], "Classe": table["classe"].map(class_label),
        "Índice (0 a 100)": table["índice de risco"].map(fmt_num), "Barra": table["índice de risco"].astype(float)})


def style_ranking(view: pd.DataFrame):
    """Cor de texto por classe (a classe continua escrita) e índice com uma casa e vírgula."""
    def cor(valor: str) -> str:
        nome = valor.split(" ", 1)[-1]
        return f"color: {CLASS_INK.get(nome, INK)}; font-weight: 700"

    return view.style.map(cor, subset=["Classe"])


RANKING_COLUMNS = {
    "Posição": st.column_config.NumberColumn("Nº", format="%d", width="small"),
    "Bairro": st.column_config.TextColumn("Bairro", width="medium"),
    "Classe": st.column_config.TextColumn("Classe", width="small"),
    "Índice (0 a 100)": st.column_config.TextColumn("Índice", width="small"),
    "Barra": st.column_config.ProgressColumn("Escala", min_value=0, max_value=100, format=" ", width="small"),
}


SERIES_COLORS = ["#0f766e", "#b4421a", "#5b6770", "#c58a1b", "#3b6ea5", "#7a4d00"]
MODEL_COLORS = {"RandomForest": "#0f766e", "Persistência": "#a3adb5"}


def sensor_status_view(estado: pd.DataFrame) -> pd.DataFrame:
    """Tabela de estado das estações com cabeçalhos em português e a tensão com vírgula."""
    return pd.DataFrame({
        "Bairro": estado["bairro"], "Última semana": estado["última semana"],
        "Leituras na última semana": estado["leituras na última semana"],
        "Semanas com dados": estado["semanas com dados"],
        "Bateria mínima (V)": estado["bateria mínima (V)"].map(lambda v: fmt_num(v, 2))})


def comparison_table_view(tabela: pd.DataFrame) -> pd.DataFrame:
    """Tabela de métricas com vírgula decimal (os valores já vêm formatados como texto com ponto)."""
    return tabela.apply(lambda col: col.map(lambda v: str(v).replace(".", ",")) if col.name != "métrica" else col)
