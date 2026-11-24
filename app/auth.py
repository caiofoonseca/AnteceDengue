"""Acesso ao dashboard por usuário e senha.

As credenciais vêm só do ambiente (DASHBOARD_USER e DASHBOARD_PASSWORD, definidas no .env). Sem credenciais
válidas o acesso fica fechado: não existe senha padrão nem modo aberto. É uma barreira da interface do
dashboard; a API continua com as regras dela. A sessão vale enquanto a aba do navegador ficar aberta.
"""
import hmac
import os
import time

import streamlit as st

from app import ui

SESSION_KEY = "auth_user"
FAILS_KEY = "auth_fails"
LOCK_KEY = "auth_locked_until"
MAX_FAILS = 5
LOCK_SECONDS = 30
PLACEHOLDER_PREFIXES = ("troque", "gere", "change", "changeme")


def auth_disabled() -> bool:
    """Login desligado só se DASHBOARD_AUTH for off, 0, false ou no (padrão: ligado)."""
    return os.getenv("DASHBOARD_AUTH", "on").strip().lower() in ("off", "0", "false", "no")


def configured_credentials() -> tuple[str, str] | None:
    """(usuário, senha) do ambiente, ou None se faltar algo ou se a senha ainda for o texto de exemplo."""
    usuario = os.getenv("DASHBOARD_USER", "").strip()
    senha = os.getenv("DASHBOARD_PASSWORD", "")
    if not usuario or not senha or senha.lower().startswith(PLACEHOLDER_PREFIXES):
        return None
    return usuario, senha


def check_credentials(usuario: str, senha: str, esperado: tuple[str, str]) -> bool:
    """Comparação em tempo constante; avalia os dois campos sempre, para não revelar qual deles errou."""
    usuario_ok = hmac.compare_digest(usuario.strip().encode("utf-8"), esperado[0].encode("utf-8"))
    senha_ok = hmac.compare_digest(senha.encode("utf-8"), esperado[1].encode("utf-8"))
    return usuario_ok and senha_ok


def is_authenticated() -> bool:
    return bool(st.session_state.get(SESSION_KEY))


def logout() -> None:
    for chave in (SESSION_KEY, FAILS_KEY, LOCK_KEY):
        st.session_state.pop(chave, None)


def seconds_locked(agora: float | None = None) -> int:
    restante = st.session_state.get(LOCK_KEY, 0) - (time.time() if agora is None else agora)
    return max(0, int(restante) + (1 if restante > 0 else 0))


def register_failure(agora: float | None = None) -> None:
    falhas = st.session_state.get(FAILS_KEY, 0) + 1
    st.session_state[FAILS_KEY] = falhas
    if falhas >= MAX_FAILS:
        st.session_state[LOCK_KEY] = (time.time() if agora is None else agora) + LOCK_SECONDS
        st.session_state[FAILS_KEY] = 0


def login_page(esperado: tuple[str, str] | None) -> None:
    """Tela de entrada: marca, formulário e aviso de uso. Chama st.stop() no fim."""
    _, centro, _ = st.columns([1, 1.15, 1])
    with centro:
        ui.render('<div class="login-brand">' + ui.logo_mark(84) + '<div class="login-title">' + ui.wordmark()
                  + '</div><div class="login-tagline">' + ui.esc(ui.TAGLINE) + '</div></div>')
        with st.container(border=True, key="card_login"):
            if esperado is None:
                st.error("Acesso não configurado. Defina DASHBOARD_USER e DASHBOARD_PASSWORD no arquivo .env "
                         "(a senha não pode ser o texto de exemplo) e reinicie o dashboard.")
            else:
                ui.render(ui.card_title("Entrar", "acesso restrito ao grupo do projeto"))
                bloqueio = seconds_locked()
                with st.form("login", border=False):
                    usuario = st.text_input("Usuário", autocomplete="username")
                    senha = st.text_input("Senha", type="password", autocomplete="current-password")
                    enviar = st.form_submit_button("Entrar", type="primary", width="stretch", disabled=bloqueio > 0)
                if bloqueio > 0:
                    st.warning(f"Muitas tentativas. Tente de novo em {bloqueio} segundos.")
                elif enviar:
                    if check_credentials(usuario, senha, esperado):
                        st.session_state[SESSION_KEY] = esperado[0]
                        st.session_state[FAILS_KEY] = 0
                        st.rerun()
                    register_failure()
                    st.error("Usuário ou senha incorretos.")
        ui.render('<div class="login-note">O índice de risco é um índice de ordenação de 0 a 100, não calibrado e '
                  'não é probabilidade de surto. Projeto G15 · CESAR School.</div>')
    st.stop()


def require_login() -> str:
    """Devolve o usuário autenticado; se não houver sessão, mostra a tela de entrada e interrompe a execução."""
    if auth_disabled():
        return ""
    if is_authenticated():
        return st.session_state[SESSION_KEY]
    login_page(configured_credentials())
    return ""


def session_bar(usuario: str) -> None:
    """Faixa fina abaixo do cabeçalho com o usuário conectado e o botão Sair."""
    if auth_disabled():
        ui.render('<div class="session-user">Modo demonstração: login desligado (DASHBOARD_AUTH=off)</div>')
        return
    texto, botao = st.columns([11, 1.4], vertical_alignment="center")
    with texto:
        ui.render(f'<div class="session-user">Conectado como <strong>{ui.esc(usuario)}</strong></div>')
    with botao:
        if st.button("Sair", key="logout", width="stretch"):
            logout()
            st.rerun()
