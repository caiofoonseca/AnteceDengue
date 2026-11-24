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
