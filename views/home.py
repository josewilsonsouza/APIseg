"""
views/home.py
Resumo geral: KPI cards, breakdown por fonte e tabela de indicadores.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import io

from ui.colors import CNSEG_ORANGE, CNSEG_TEAL, CNSEG_RED
from ui.toc import render_toc, anchor
from ui.kpi import kpi
import loaders.apis as api_loader

_AMARELO = "#FFD114"


def render(ctx) -> None:
    log = st.session_state.get("ultimo_log")
    render_toc([
        ("KPI Cards",            "home-kpi"),
        ("Status por Fonte",     "home-chart"),
        ("Resumo por Indicador", "home-tabela"),
        *([("Log de Execução",   "home-log")] if log else []),
    ])

    _corte_label = ""
    if ctx.corte_ano:
        _meses = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                  7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
        _corte_label = f"  —  até {_meses[ctx.corte_mes]}/{ctx.corte_ano}"

    st.title(f"APIseg — Validação de Indicadores{_corte_label}", text_alignment="center")
    st.markdown("---")

    # ── Agrega KPIs ───────────────────────────────────────────────────────────
    total = n_ok = n_divs = n_risco = 0
    for fonte in ctx.fontes:
        df_r = ctx.resumos.get(fonte)
        if df_r is not None and not df_r.empty:
            total += len(df_r)
            n_ok  += int(df_r["Status"].str.contains("✔").sum())

        # Divergências contadas a partir dos dados já filtrados pelo corte
        df_d = ctx.divergencias.get(fonte)
        if df_d is not None and not df_d.empty:
            n_divs += int((df_d["Tipo"] == "Valores diferentes").sum()
                          + (df_d["Tipo"] == "Período ausente na API").sum()
                          + (df_d["Tipo"] == "Período ausente no Cognos").sum())

        df_a = ctx.atualizacoes.get(fonte)
        if df_a is not None and not df_a.empty:
            n_risco += int(df_a["Status"].str.contains("🔴").sum())

    anchor("home-kpi")
    c1, c2, c3, c4 = st.columns(4)
    pct_ok = f"{n_ok / total * 100:.0f}%" if total else "—"

    with c1:
        with st.container(border=True):
            kpi("📋 Total de Indicadores", str(total), CNSEG_ORANGE)
    with c2:
        with st.container(border=True):
            kpi("✅ OK", f'{n_ok} <span style="font-size:1rem;font-weight:400;opacity:0.7">{pct_ok}</span>', CNSEG_TEAL)
    with c3:
        with st.container(border=True):
            kpi("❌ Divergências", str(n_divs), CNSEG_RED if n_divs > 0 else CNSEG_TEAL)
    with c4:
        with st.container(border=True):
            kpi("🔴 Séries em Risco", str(n_risco), CNSEG_RED if n_risco > 0 else CNSEG_TEAL)

    st.markdown("---")

    # ── Breakdown por fonte ───────────────────────────────────────────────────
    anchor("home-chart")
    st.subheader("Status por Fonte")

    rows = []
    for fonte in ctx.fontes:
        df_r = ctx.resumos.get(fonte)
        if df_r is None or df_r.empty:
            continue
        rows.append({
            "Fonte":       ctx.fonte_labels[fonte],
            "OK":          int(df_r["Status"].str.contains("✔").sum()),
            "Divergência": int(df_r["Status"].str.contains("❌").sum()),
            "Aviso":       int(df_r["Status"].str.contains("⚠").sum()),
        })

    if rows:
        df_chart = pd.DataFrame(rows)
        fig = go.Figure()
        for cat, color in [("OK", CNSEG_TEAL), ("Divergência", CNSEG_RED), ("Aviso", _AMARELO)]:
            fig.add_trace(go.Bar(
                name=cat,
                x=df_chart["Fonte"],
                y=df_chart[cat],
                marker_color=color,
                text=df_chart[cat],
                textposition="auto",
            ))
        fig.update_layout(
            barmode="stack",
            height=280,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    else:
        st.info("Nenhum relatório encontrado. Execute `python run.py` para gerar os dados.")

    # ── Tabela resumo ─────────────────────────────────────────────────────────
    anchor("home-tabela")
    with st.expander("Resumo por Indicador", expanded=False):
        frames = []
        for fonte in ctx.fontes:
            df_r = ctx.resumos.get(fonte)
            if df_r is not None and not df_r.empty:
                df_r = df_r.copy()
                df_r.insert(0, "Fonte", ctx.fonte_labels[fonte])
                frames.append(df_r)

        if frames:
            df_all = pd.concat(frames, ignore_index=True)
            st.dataframe(
                df_all,
                width='stretch',
                hide_index=True,
                column_config={
                    "Fonte":             st.column_config.TextColumn("Fonte", width="small"),
                    "Indicador":         st.column_config.TextColumn("Indicador", width="large"),
                    "Registros API":     st.column_config.NumberColumn("API", format="%d"),
                    "Registros Cognos":  st.column_config.NumberColumn("Cognos", format="%d"),
                    "Coincidentes":      st.column_config.NumberColumn("Coinc.", format="%d"),
                    "Divergências":      st.column_config.TextColumn("Diverg."),
                    "Status":            st.column_config.TextColumn("Status"),
                },
            )
        else:
            st.info("Nenhum relatório encontrado. Execute `python run.py` para gerar os dados.")

    # ── Exportar dados brutos da API ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Exportar Dados da API")
    cols = st.columns(len(ctx.fontes))
    for col, fonte in zip(cols, ctx.fontes):
        with col:
            df_api = api_loader.load_dados_api(fonte)
            label  = ctx.fonte_labels[fonte]
            if df_api is not None and not df_api.empty:
                buf = io.BytesIO()
                df_api.to_excel(buf, index=False)
                st.download_button(
                    label=f"⬇ {label}",
                    data=buf.getvalue(),
                    file_name=f"dados_api_{fonte}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"export_api_{fonte}",
                )
                st.caption(f"{len(df_api):,} períodos · {len(df_api.columns) - 2} indicadores")
            else:
                st.button(f"⬇ {label}", disabled=True, key=f"export_api_{fonte}_dis")
                st.caption("Sem dados — execute a validação")

    # ── Log da última execução ────────────────────────────────────────────────
    log = st.session_state.get("ultimo_log")
    if log:
        anchor("home-log")
        st.markdown("---")

        sucesso    = log["sucesso"]
        status_cor = CNSEG_TEAL if sucesso else CNSEG_RED
        status_txt = "Sucesso" if sucesso else "Erro"
        status_ico = "✔" if sucesso else "✖"
        fontes_txt = " · ".join(f.upper() for f in log["fontes"])

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem">'
            f'<span style="font-size:1.1rem;font-weight:700">📋 Log da última execução</span>'
            f'<span style="background:{status_cor}22;color:{status_cor};font-weight:600;'
            f'padding:2px 10px;border-radius:20px;font-size:0.82rem">'
            f'{status_ico} {status_txt}</span>'
            f'<span style="font-size:0.8rem;opacity:0.55">{log["timestamp"]} · {fontes_txt}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.expander("Ver saída completa", expanded=not sucesso):
            if log["stdout"].strip():
                st.code(log["stdout"], language=None)
            if log["stderr"].strip():
                st.markdown(
                    f'<p style="color:{CNSEG_RED};font-size:0.82rem;font-weight:600;margin:0.5rem 0 0.2rem">Stderr:</p>',
                    unsafe_allow_html=True,
                )
                st.code(log["stderr"], language=None)
            if not log["stdout"].strip() and not log["stderr"].strip():
                st.caption("Nenhuma saída registrada.")
