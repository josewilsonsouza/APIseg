"""
ui/sidebar.py — Sidebar do APIseg.
Retorna corte_ano, corte_mes, fontes_sel via SimpleNamespace.
"""

import sys
from pathlib import Path

import streamlit as st

from ui.colors import CNSEG_ORANGE, CNSEG_BLUE, CNSEG_TEAL
import loaders.apis as api_loader

ROOT = Path(__file__).parent.parent

_MESES_ABREV = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
                7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

PAGINAS = ["📊 Resumo", "🔍 Divergências", "🔄 Atualização de Séries"]

FONTE_LABELS = {"bacen": "BACEN", "ibge": "IBGE", "ipea": "IPEA"}
FONTE_CORES  = {"bacen": CNSEG_ORANGE, "ibge": CNSEG_BLUE, "ipea": CNSEG_TEAL}


def render_sidebar():
    with st.sidebar:
        st.markdown(
            f'<p style="font-size:1.3rem;font-weight:700;margin:0;color:{CNSEG_ORANGE}">📡 APIseg</p>'
            f'<p style="font-size:0.78rem;opacity:0.7;margin:0 0 0.5rem">Validação de Indicadores</p>',
            unsafe_allow_html=True,
        )
        st.write("---")

        # ── Navegação ─────────────────────────────────────────────────────────
        if "pagina_ativa" not in st.session_state:
            st.session_state.pagina_ativa = 0

        for i, titulo in enumerate(PAGINAS):
            if i == st.session_state.pagina_ativa:
                st.markdown(
                    f'<div class="sidebar-button-active" '
                    f'style="border-bottom-color:{CNSEG_ORANGE};">{titulo}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(titulo, key=f"nav_{i}", width='stretch'):
                    st.session_state.pagina_ativa = i
                    st.session_state.scroll_to_top = True
                    st.rerun()

        st.write("---")

        # ── Período de corte ──────────────────────────────────────────────────
        _periodos_disp = api_loader.load_periodos_disponiveis(["bacen", "ibge", "ipea"])
        if _periodos_disp:
            _ultimo_ano, _ultimo_mes = _periodos_disp[-1]
            _min_ano = _ultimo_ano - 3

            _periodos_opcoes = sorted(
                [p for p in _periodos_disp if p[0] >= _min_ano], reverse=True
            )

            if "corte_periodo" not in st.session_state:
                st.session_state.corte_periodo = (_ultimo_ano, _ultimo_mes)

            st.caption("**Período de corte**")
            _periodo_sel = st.selectbox(
                "Período",
                _periodos_opcoes,
                index=_periodos_opcoes.index(st.session_state.corte_periodo)
                      if st.session_state.corte_periodo in _periodos_opcoes else 0,
                format_func=lambda p: f"{_MESES_ABREV[p[1]]}/{str(p[0])[2:]}",
                label_visibility="collapsed",
                key="corte_periodo_sel",
            )
            st.session_state.corte_periodo = _periodo_sel
            corte_ano, corte_mes = st.session_state.corte_periodo
        else:
            corte_ano, corte_mes = None, None

        fontes_sel = ["bacen", "ibge", "ipea"]

        st.write("---")

        # ── Executar validação ────────────────────────────────────────────────
        with st.expander("▶ Executar validação"):
            st.caption("Fontes a validar:")
            _run_fontes = [
                f for f in ("bacen", "ibge", "ipea")
                if st.checkbox(FONTE_LABELS[f], value=True, key=f"run_fonte_{f}")
            ]
            _executar = st.button("▶ Executar", width='stretch', key="run_exec")

        if _executar:
            import subprocess, os
            fontes_run = _run_fontes or ["bacen", "ibge", "ipea"]
            label_run  = " ".join(FONTE_LABELS[f] for f in fontes_run)
            with st.spinner(f"Executando: {label_run} …"):
                _env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                result = subprocess.run(
                    [sys.executable, str(ROOT / "run.py")] + fontes_run,
                    capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT), env=_env,
                )
            if result.returncode == 0:
                api_loader.clear_cache()
                st.success("Concluído!")
                st.rerun()
            else:
                st.error(f"Erro na execução:\n\n```\n{result.stderr[-600:]}\n```")

        st.write("---")

        # ── Última execução ───────────────────────────────────────────────────
        st.caption("**Última execução**")
        for fonte in ("bacen", "ibge", "ipea"):
            mtime = api_loader.report_mtime(fonte)
            cor   = FONTE_CORES[fonte]
            label = FONTE_LABELS[fonte]
            if mtime:
                st.markdown(
                    f'<span style="color:{cor};font-weight:600">{label}</span>'
                    f'<span style="font-size:0.78rem;opacity:0.8">&nbsp;{mtime}</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"• {label}: sem dados")

    return corte_ano, corte_mes, fontes_sel
