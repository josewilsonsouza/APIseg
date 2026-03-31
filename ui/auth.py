"""
ui/auth.py - Gate de autenticação do AMseg.

Suporta três modos (detectados automaticamente via secrets.toml):
  1. Senha única       -> APP_PASSWORD definido
  2. OAuth (Google / Microsoft / Okta) -> bloco [auth] definido
  3. Dev bypass        -> nenhum dos dois (acesso liberado)

No momento estamos utilizando apenas o modo senha, por ser o mais simples de configurar 
para os usuários corporativos. O modo OAuth é uma opção futura caso haja demanda por SSO via 
"""

import base64
import streamlit as st
from ui.colors import CNSEG_ORANGE
from ui.toc import render_toc
# Internos

def _auth_providers() -> list[tuple[str, str, str]]:
    """
    Retorna lista de (provider_key, label, icon) configurados em secrets.toml.
    Suporta bloco único [auth] (provider=None) ou múltiplos [auth.xxx].
    """
    try:
        auth_cfg = st.secrets.get("auth", {})
    except Exception:
        return []
    if not auth_cfg:
        return []

    _KNOWN = {
        "microsoft": ("Microsoft", "🪟"),
        "google":    ("Google",    "🔵"),
        "okta":      ("Okta",      "🔐"),
    }
    providers = []
    for key in auth_cfg:
        sub = auth_cfg.get(key, {})
        if isinstance(sub, dict) and sub.get("client_id"):
            label, icon = _KNOWN.get(key, (key.capitalize(), "🔑"))
            providers.append((key, label, icon))

    # Provider único no bloco raiz
    if not providers and auth_cfg.get("client_id"):
        providers.append((None, "SSO corporativo", "🔑"))

    return providers


def _render_login() -> None:
    """Página de login exibida quando o usuário não está autenticado."""
    render_toc([])  # remove TOC flutuante de páginas anteriores

    # Esconde sidebar e adiciona animação de loading à imagem do logo, para fazer a imagem rodar mais rápido e
    # podemos ativar a rotação: animation: spin 6s linear infinite;
    # alterar o paramentro: 6s, quanto menor for, mais rapido será
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to   { transform: rotate(360deg); }
        }
        .spin-logo {
            display: block;
            margin: 0 auto 1.5rem auto;
            width: 120px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _img_b64 = base64.b64encode(open("images/icone-agente.png", "rb").read()).decode()
    _, _col, _ = st.columns([1, 1.2, 1])
    with _col:
        st.markdown(
            f'<a href="https://www.cnseg.org.br/" target="_blank">'
            f'<img class="spin-logo" src="data:image/png;base64,{_img_b64}">'
            f'</a>',
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='text-align:center'>"
            #f"<h1 style='margin-bottom:0.1rem;color:{CNSEG_ORANGE}'>AMseg</h1>"
            f"<h1 style='color:{CNSEG_ORANGE};margin-bottom:1.5rem'>Acompanhamento Mensal do Setor Segurador</h1>"
            "</div>",
            unsafe_allow_html=True,
        )

        _senha_conf = st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") else ""
        _providers  = _auth_providers()

        if _senha_conf:
            # Modo senha - form captura Enter além do clique no botão
            with st.form("_login_form"):

                senha = st.text_input("Senha de acesso", 
                                    type="password", 
                                    placeholder="Informe a senha de acesso",
                                    icon="🔑",)
                st.write("")  # espaçamento
                submitted = st.form_submit_button("Entrar",
                                                use_container_width=True,
                                                type="primary",
                                                icon="🔓")
            
            if submitted:
                if senha == _senha_conf:
                    st.session_state["_autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")

        elif _providers:
            # Modo OAuth — providers configurados em secrets.toml
            if len(_providers) == 1:
                provider, label, icon = _providers[0]
                if st.button(f"{icon}  Entrar com {label}", use_container_width=True, type="primary"):
                    st.login(provider)
            else:
                for provider, label, icon in _providers:
                    if st.button(f"{icon}  Entrar com {label}", use_container_width=True):
                        st.login(provider)

        else:
            # Sem auth configurado — acesso liberado (dev)
            st.info("Autenticação não configurada em `secrets.toml` — acesso liberado.")
            if st.button("Entrar sem autenticação", use_container_width=True):
                st.session_state["_dev_bypass"] = True
                st.rerun()


# Públicos — chamados em app.py

def check_auth() -> None:
    """
    Verifica se o usuário está autenticado.
    Exibe a página de login e chama st.stop() se não estiver.
    Ordem de precedência: senha > OAuth > dev bypass.
    """
    _senha_conf      = st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") else ""
    _autenticado     = st.session_state.get("_autenticado", False)
    _auth_configured = bool(st.secrets.get("auth", {}) if hasattr(st, "secrets") else {})

    if (_senha_conf and not _autenticado) or (_auth_configured and not st.user.is_logged_in):
        _render_login()
        st.stop()


def render_sair_button() -> None:
    """
    Exibe botão 'Sair' no rodapé do sidebar quando autenticação por senha está ativa.
    Deve ser chamado após render_sidebar().
    """
    _senha_conf  = st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") else ""
    _autenticado = st.session_state.get("_autenticado", False)

    if _senha_conf and _autenticado:
        st.sidebar.markdown("---")
        if st.sidebar.button("↩ Sair", use_container_width=True):
            st.session_state.pop("_autenticado", None)
            st.rerun()
