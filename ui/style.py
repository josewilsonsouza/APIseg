from pathlib import Path
import streamlit as st


def aplicar_estilo(css_file: str = "ui/styles.css") -> None:
    """Carrega e injeta o CSS externo no Streamlit."""
    css_path = Path(css_file)
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
