"""Carrega os arquivos Cognos de data/cognos/."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
COGNOS_DIR = ROOT / "data" / "cognos"

_FONTE_FILES = {
    "bacen": "Indicadores BACEN.xlsx",
    "ibge":  "Indicadores IBGE.xlsx",
    "ipea":  "Indicadores IPEA.xlsx",
}


@st.cache_data(ttl=3600, show_spinner=False)
def load_cognos(fonte: str) -> pd.DataFrame | None:
    """Lê o arquivo Cognos da fonte informada (aba Página1_1)."""
    p = COGNOS_DIR / _FONTE_FILES.get(fonte, "")
    if not p.exists():
        return None
    try:
        return pd.read_excel(p, sheet_name="Página1_1")
    except Exception:
        try:
            return pd.read_excel(p, sheet_name=0)
        except Exception:
            return None
