"""Carrega os outputs gerados pelos validadores (outputs/)."""

import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = ROOT / "outputs"

FONTES = ("bacen", "ibge", "ipea")
FONTE_LABELS = {"bacen": "BACEN", "ibge": "IBGE", "ipea": "IPEA"}


def _report_path(fonte: str) -> Path:
    return OUTPUTS_DIR / "divergencias" / f"divergencias_{fonte}.xlsx"


def _dados_path(fonte: str) -> Path:
    return OUTPUTS_DIR / "dados" / f"dados_api_{fonte}.xlsx"


@st.cache_data(ttl=300, show_spinner=False)
def load_resumo(fonte: str) -> pd.DataFrame | None:
    p = _report_path(fonte)
    if not p.exists():
        return None
    try:
        return pd.read_excel(p, sheet_name="Resumo")
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_divergencias(fonte: str) -> pd.DataFrame | None:
    p = _report_path(fonte)
    if not p.exists():
        return None
    try:
        return pd.read_excel(p, sheet_name="Todas as divergências")
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_atualizacao(fonte: str) -> pd.DataFrame | None:
    p = _report_path(fonte)
    if not p.exists():
        return None
    try:
        return pd.read_excel(p, sheet_name="Atualização séries")
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_dados_api(fonte: str) -> pd.DataFrame | None:
    p = _dados_path(fonte)
    if not p.exists():
        return None
    try:
        return pd.read_excel(p)
    except Exception:
        return None


def report_mtime(fonte: str) -> str | None:
    """Retorna data/hora da última modificação do relatório de divergências."""
    p = _report_path(fonte)
    if not p.exists():
        return None
    from zoneinfo import ZoneInfo
    ts = p.stat().st_mtime
    return datetime.datetime.fromtimestamp(ts, tz=ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")


def clear_cache() -> None:
    """Limpa todos os caches de dados."""
    load_resumo.clear()
    load_divergencias.clear()
    load_atualizacao.clear()
    load_dados_api.clear()


def load_periodos_disponiveis(fontes: list[str]) -> list[tuple[int, int]]:
    """Retorna lista ordenada de (ano, mes) disponíveis nos dados da API das fontes."""
    periodos: set[tuple[int, int]] = set()
    for fonte in fontes:
        df = load_dados_api(fonte)
        if df is None or df.empty or "Ano" not in df.columns or "Mês" not in df.columns:
            continue
        for ano, mes in df[["Ano", "Mês"]].drop_duplicates().itertuples(index=False):
            try:
                periodos.add((int(ano), int(mes)))
            except (ValueError, TypeError):
                pass
    return sorted(periodos)


def computa_resumo_corte(
    dados_api: pd.DataFrame,
    divergencias: pd.DataFrame | None,
) -> pd.DataFrame:
    """Recomputa resumo por indicador com base nos dados já filtrados pelo corte."""
    indicadores = [c for c in dados_api.columns if c not in ("Ano", "Mês")]
    rows = []
    for ind in indicadores:
        reg_api = int(dados_api[ind].notna().sum())
        n_divs = 0
        if divergencias is not None and not divergencias.empty and "Indicador" in divergencias.columns:
            n_divs = int((divergencias["Indicador"] == ind).sum())
        status = "✔ OK" if n_divs == 0 else f"❌ {n_divs} divergência(s)"
        rows.append({"Indicador": ind, "Registros API": reg_api, "Divergências": n_divs, "Status": status})
    return pd.DataFrame(rows)


def computa_atualizacao_corte(
    dados_api: pd.DataFrame,
    corte_ano: int,
    corte_mes: int,
    threshold_mensal: int = 4,
    threshold_trimestral: int = 6,
) -> pd.DataFrame:
    """
    Recomputa status de atualização de séries usando o corte como data de referência.
    Diferente de verifica_atualizacao(), que usa date.today(), aqui a defasagem é
    medida a partir de (corte_ano, corte_mes).
    """
    from datetime import date

    mask = (dados_api["Ano"] < corte_ano) | (
        (dados_api["Ano"] == corte_ano) & (dados_api["Mês"] <= corte_mes)
    )
    df = dados_api[mask].copy()

    indicadores = [c for c in df.columns if c not in ("Ano", "Mês")]
    ref = date(corte_ano, corte_mes, 1)
    rows = []

    for ind in indicadores:
        sub = df[df[ind].notna()][["Ano", "Mês"]]
        if sub.empty:
            rows.append({
                "Indicador": ind, "Último Ano": None, "Último Mês": None,
                "Meses sem atualização": None, "Periodicidade": "desconhecida",
                "Status": "⚠️ Sem dados na API",
            })
            continue

        ultimo_ano = int(sub["Ano"].max())
        ultimo_mes = int(sub.loc[sub["Ano"] == sub["Ano"].max(), "Mês"].max())
        meses = (ref.year - ultimo_ano) * 12 + (ref.month - ultimo_mes)

        meses_unicos = sorted(df["Mês"].unique())
        e_trimestral = all(m % 3 == 0 for m in meses_unicos) and len(meses_unicos) <= 4
        periodicidade = "trimestral" if e_trimestral else "mensal"
        threshold = threshold_trimestral if e_trimestral else threshold_mensal

        if meses > threshold:
            status = f"🔴 Possível descontinuação ({meses} meses sem atualização)"
        else:
            status = f"✔️ Atualizada ({meses} mês(es) de defasagem)"

        rows.append({
            "Indicador": ind, "Último Ano": ultimo_ano, "Último Mês": ultimo_mes,
            "Meses sem atualização": meses, "Periodicidade": periodicidade, "Status": status,
        })

    return pd.DataFrame(rows)
