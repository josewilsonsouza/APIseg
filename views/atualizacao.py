"""
views/atualizacao.py
Status de atualização das séries — detecta possíveis descontinuações.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.colors import CNSEG_TEAL, CNSEG_RED, CNSEG_GRAY
from ui.toc import render_toc, anchor


def _cor_status(status: str) -> str:
    if "🔴" in status:
        return CNSEG_RED
    if "✔" in status:
        return CNSEG_TEAL
    return CNSEG_GRAY


def render(ctx) -> None:
    render_toc([
        ("KPI Cards",   "atu-kpi"),
        ("Tabela",      "atu-tabela"),
        ("Defasagem",   "atu-chart"),
    ])

    _corte_label = ""
    if ctx.corte_ano:
        _meses = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                  7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
        _corte_label = f"  —  até {_meses[ctx.corte_mes]}/{ctx.corte_ano}"

    st.title(f"Atualização de Séries{_corte_label}", text_alignment="center")
    st.markdown("---")

    # ── Combina dados ─────────────────────────────────────────────────────────
    frames = []
    for fonte in ctx.fontes:
        df = ctx.atualizacoes.get(fonte)
        if df is not None and not df.empty:
            df = df.copy()
            df.insert(0, "Fonte", ctx.fonte_labels[fonte])
            frames.append(df)

    if not frames:
        st.info("Nenhum dado de atualização disponível. Execute `python run.py` para gerar.")
        return

    df_all = pd.concat(frames, ignore_index=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    anchor("atu-kpi")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.metric("📊 Total de Séries", len(df_all))
    with c2:
        with st.container(border=True):
            st.metric("✅ Atualizadas", int(df_all["Status"].str.contains("✔").sum()))
    with c3:
        with st.container(border=True):
            st.metric("🔴 Possível Descontinuação", int(df_all["Status"].str.contains("🔴").sum()))
    with c4:
        with st.container(border=True):
            st.metric("⚠️ Sem dados na API", int(df_all["Status"].str.contains("⚠").sum()))

    st.markdown("---")

    # ── Filtros ───────────────────────────────────────────────────────────────
    anchor("atu-tabela")
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        fontes_disp = sorted(df_all["Fonte"].unique())
        sel_fontes = st.multiselect("Fonte", fontes_disp, default=fontes_disp, key="atu_fontes")
    with col_f2:
        status_opts = ["Todas", "✅ Atualizadas", "🔴 Em risco", "⚠️ Sem dados"]
        sel_status = st.selectbox("Status", status_opts, key="atu_status")

    mask = pd.Series(True, index=df_all.index)
    if sel_fontes:
        mask &= df_all["Fonte"].isin(sel_fontes)
    if sel_status == "✅ Atualizadas":
        mask &= df_all["Status"].str.contains("✔")
    elif sel_status == "🔴 Em risco":
        mask &= df_all["Status"].str.contains("🔴")
    elif sel_status == "⚠️ Sem dados":
        mask &= df_all["Status"].str.contains("⚠")

    df_filt = df_all[mask].sort_values(
        "Meses sem atualização", ascending=False, na_position="last"
    )

    # ── Tabela ────────────────────────────────────────────────────────────────
    st.dataframe(
        df_filt,
        width='stretch',
        hide_index=True,
        height=400,
        column_config={
            "Fonte":                 st.column_config.TextColumn("Fonte", width="small"),
            "Indicador":             st.column_config.TextColumn("Indicador", width="large"),
            "Último Ano":            st.column_config.NumberColumn("Último Ano", format="%d", width="small"),
            "Último Mês":            st.column_config.NumberColumn("Último Mês", format="%d", width="small"),
            "Meses sem atualização": st.column_config.NumberColumn("Meses s/ atualiz.", format="%d"),
            "Periodicidade":         st.column_config.TextColumn("Periodicidade", width="small"),
            "Status":                st.column_config.TextColumn("Status"),
        },
    )

    # ── Gráfico de defasagem ──────────────────────────────────────────────────
    anchor("atu-chart")
    st.subheader("Defasagem por Indicador")

    df_chart = df_filt[df_filt["Meses sem atualização"].notna()].copy()
    if df_chart.empty:
        return

    df_chart["_cor"]   = df_chart["Status"].apply(_cor_status)
    df_chart["_label"] = df_chart["Fonte"] + " · " + df_chart["Indicador"]
    df_chart = df_chart.sort_values("Meses sem atualização", ascending=True)

    fig = px.bar(
        df_chart,
        x="Meses sem atualização",
        y="_label",
        orientation="h",
        color="_cor",
        color_discrete_map="identity",
        text="Meses sem atualização",
    )
    fig.update_layout(
        height=max(350, len(df_chart) * 28),
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        yaxis=dict(tickfont=dict(size=10), title=""),
        xaxis=dict(title="Meses sem atualização"),
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
