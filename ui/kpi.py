"""
ui/kpi.py
Componentes reutilizáveis de KPI e UI para todas as views.
"""

import streamlit as st

from ui.colors import CNSEG_TEAL, CNSEG_RED, CNSEG_GRAY


def kpi(label: str, 
        value: str, 
        color: str, 
        delta: str = None, 
        delta_color: 
        str = None) -> None:
    """Renderiza um card KPI com label, valor principal e delta opcional."""
    parts = [
        f'<p style="font-size:0.85rem;margin:0;opacity:0.65">{label}</p>',
        f'<p style="font-size:1.9rem;font-weight:700;margin:0.15rem 0 0;line-height:1.2">'
        f'<span style="color:{color}">{value}</span></p>',
    ]
    if delta:
        dc = delta_color or "inherit"
        bg = f"{dc}22" if delta_color else "transparent"
        parts.append(
            f'<p style="font-size:0.8rem;margin:0.1rem 0 0">'
            f'<span style="color:{dc};background-color:{bg};'
            f'padding:0.1rem 0.45rem;border-radius:4px">{delta}</span></p>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def delta_inline(val, suffix: str = "A/A", higher_is_worse: bool = False, fmt_fn=None) -> str:
    """
    Retorna HTML de badge de variação inline (seta + valor + sufixo).

    Parâmetros
    ----------
    val             : float | None — valor da variação
    suffix          : str          — texto após o valor (ex: "A/A", "p.p.")
    higher_is_worse : bool         — True para sinistros/sinistralidade (crescimento = vermelho)
    fmt_fn          : callable     — formatador; padrão fmt_pct de utils.formatting
    """
    if val is None:
        return ""
    if fmt_fn is None:
        from utils.formatting import fmt_pct
        fmt_fn = fmt_pct
    if higher_is_worse:
        _c = CNSEG_RED if val > 0 else (CNSEG_TEAL if val < 0 else CNSEG_GRAY)
    else:
        _c = CNSEG_TEAL if val > 0 else (CNSEG_RED if val < 0 else CNSEG_GRAY)
    _a = "↑" if val > 0 else ("↓" if val < 0 else "")
    return f'&nbsp;<span style="font-size:0.8rem;color:{_c}">{_a} {fmt_fn(val)} {suffix}</span>'


def render_fontes(ctx) -> None:
    """Exibe bloco de fontes no final de cada view."""
    sources = getattr(ctx, "dataseg_sources", [])
    if not sources:
        return
    with st.container(border=True):
        st.caption("**Fontes:**  " + "  \n".join(sources))
