"""
app.py — APIseg: Validação de Indicadores das APIs Socioeconômicas

Uso:
    streamlit run app.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from ui.style import aplicar_estilo
from ui.toc import scroll_to_top
from ui.sidebar import render_sidebar, FONTE_LABELS, FONTE_CORES
import loaders.apis as api_loader

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="APIseg",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo()

# ── Sidebar ───────────────────────────────────────────────────────────────────
corte_ano, corte_mes, fontes_sel = render_sidebar()

# ── Carrega e filtra dados pelo corte ────────────────────────────────────────
def _filtra_diverg(df, ano, mes):
    if df is None or df.empty or ano is None:
        return df
    mask = (df["Ano"] < ano) | ((df["Ano"] == ano) & (df["Mês"] <= mes))
    return df[mask].copy()

resumos      = {}
atualizacoes = {}
divergencias = {}

for f in fontes_sel:
    df_div = api_loader.load_divergencias(f)
    divergencias[f] = _filtra_diverg(df_div, corte_ano, corte_mes)

    df_api = api_loader.load_dados_api(f)
    if df_api is not None and not df_api.empty and corte_ano is not None:
        mask_corte = (df_api["Ano"] < corte_ano) | ((df_api["Ano"] == corte_ano) & (df_api["Mês"] <= corte_mes))
        df_api_filt = df_api[mask_corte]
        resumos[f]      = api_loader.computa_resumo_corte(df_api_filt, divergencias[f])
        atualizacoes[f] = api_loader.computa_atualizacao_corte(df_api, corte_ano, corte_mes)
    else:
        resumos[f]      = api_loader.load_resumo(f)
        atualizacoes[f] = api_loader.load_atualizacao(f)

ctx = SimpleNamespace(
    fontes       = fontes_sel,
    fonte_labels = FONTE_LABELS,
    fonte_cores  = FONTE_CORES,
    resumos      = resumos,
    divergencias = divergencias,
    atualizacoes = atualizacoes,
    corte_ano    = corte_ano,
    corte_mes    = corte_mes,
)

# ── Dispatch ──────────────────────────────────────────────────────────────────
_pagina = st.session_state.pagina_ativa
if _pagina == 0:
    import views.home as _view
elif _pagina == 1:
    import views.divergencias as _view
else:
    import views.atualizacao as _view

_view.render(ctx)
scroll_to_top()
