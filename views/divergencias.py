"""
views/divergencias.py
Explorador de divergências com filtros, tabela e gráfico de top indicadores.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.toc import render_toc, anchor


def render(ctx) -> None:
    render_toc([
        ("Filtros & Tabela", "div-tabela"),
        ("Top Indicadores",  "div-chart"),
    ])

    _meses = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
              7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
    _corte = (f"  —  até {_meses[ctx.corte_mes]}/{ctx.corte_ano}"
              if ctx.corte_ano else "")
    st.title(f"Divergências{_corte}", text_alignment="center")
    st.markdown("---")

    # ── Combina dados de todas as fontes selecionadas ─────────────────────────
    frames = []
    for fonte in ctx.fontes:
        df = ctx.divergencias.get(fonte)
        if df is not None and not df.empty:
            df = df.copy()
            df.insert(0, "Fonte", ctx.fonte_labels[fonte])
            frames.append(df)

    if not frames:
        st.info("Nenhuma divergência encontrada. Execute `python run.py` para gerar os relatórios.")
        return

    df_all = pd.concat(frames, ignore_index=True)

    anchor("div-tabela")

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([3, 3.5, 2])
    with col_f1:
        fontes_disp = sorted(df_all["Fonte"].unique())
        sel_fontes = st.multiselect("Fonte", fontes_disp, default=fontes_disp, key="div_fontes")
    with col_f2:
        tipos_disp = sorted(df_all["Tipo"].unique()) if "Tipo" in df_all.columns else []
        sel_tipos = st.multiselect("Tipo", tipos_disp, default=tipos_disp, key="div_tipos")
    with col_f3:
        busca = st.text_input("Buscar indicador", placeholder="Digite para filtrar...", key="div_busca")

    # Aplica filtros
    mask = pd.Series(True, index=df_all.index)
    if sel_fontes:
        mask &= df_all["Fonte"].isin(sel_fontes)
    if sel_tipos and "Tipo" in df_all.columns:
        mask &= df_all["Tipo"].isin(sel_tipos)
    if busca:
        mask &= df_all["Indicador"].str.contains(busca, case=False, na=False)

    df_filt = df_all[mask]

    col_info, col_btn = st.columns([6, 1])
    with col_info:
        st.caption(f"{len(df_filt):,} registros exibidos de {len(df_all):,} no total")
    with col_btn:
        from utils.tables import export_divergencias_excel
        st.download_button(
            label="⬇ Exportar",
            data=export_divergencias_excel(df_filt),
            file_name="divergencias_filtradas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="div_export",
        )

    # ── Tabela ────────────────────────────────────────────────────────────────
    st.dataframe(
        df_filt,
        width='stretch',
        hide_index=True,
        height=420,
        column_config={
            "Fonte":                  st.column_config.TextColumn("Fonte", width="small"),
            "Indicador":              st.column_config.TextColumn("Indicador", width="large"),
            "Ano":                    st.column_config.NumberColumn("Ano", format="%d", width="small"),
            "Mês":                    st.column_config.NumberColumn("Mês", format="%d", width="small"),
            "Valor API":              st.column_config.NumberColumn("Valor API", format="%.4f"),
            "Valor Cognos":           st.column_config.NumberColumn("Valor Cognos", format="%.4f"),
            "Diferença Absoluta":     st.column_config.NumberColumn("Dif. Abs.", format="%.4f"),
            "Diferença Relativa (%)": st.column_config.NumberColumn("Dif. Rel. (%)", format="%.4f"),
            "Tipo":                   st.column_config.TextColumn("Tipo"),
        },
    )

    # ── Top indicadores com mais divergências ─────────────────────────────────
    anchor("div-chart")
    st.subheader("Top 15 Indicadores com Mais Divergências")

    top = (
        df_filt.groupby(["Fonte", "Indicador"])
        .size()
        .reset_index(name="Qtd")
        .sort_values("Qtd", ascending=True)
        .tail(15)
    )

    if top.empty:
        st.info("Nenhuma divergência nos dados filtrados.")
        return

    color_map = {ctx.fonte_labels[f]: ctx.fonte_cores[f] for f in ctx.fontes}

    fig = px.bar(
        top,
        x="Qtd",
        y="Indicador",
        color="Fonte",
        orientation="h",
        color_discrete_map=color_map,
        text="Qtd",
    )
    fig.update_layout(
        height=max(300, len(top) * 34),
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=len(ctx.fontes) > 1,
        yaxis=dict(tickfont=dict(size=11), title=""),
        xaxis=dict(title="Nº de divergências"),
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
