"""
utils/formatting.py
Helpers de formatação numérica e de labels no padrão brasileiro.
"""


def _br(val: float, fmt: str) -> str:
    """Formata número no padrão brasileiro (. milhar, , decimal)."""
    s = format(val, fmt)
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def prev_month(yyyymm: int) -> int:
    """Retorna o mês anterior em formato YYYYMM."""
    y, m = divmod(yyyymm, 100)
    return (y - 1) * 100 + 12 if m == 1 else y * 100 + (m - 1)


def short_lbl(lbl: str) -> str:
    """'Dez/2025' -> 'dez-25'"""
    parts = lbl.split("/")
    if len(parts) == 2:
        return f"{parts[0].lower()}-{parts[1][-2:]}"
    return lbl


# ---------------------------------------------------------------------------
# Constantes de hierarquia de dados
# ---------------------------------------------------------------------------

# Mapeia label do seletor de nível -> coluna do DataFrame
LEVEL_COL: dict[str, str] = {
    "Segmento": "segmento",
    "Grupo":    "grupo1",
    "Ramo":     "grupo2",
}

# ---------------------------------------------------------------------------
# Formatadores de display (retornam strings prontas para exibição)
# ---------------------------------------------------------------------------

def fmt_bi(val: float) -> str:
    """R$ 1,23 bi"""
    return f"R$ {_br(val / 1e9, ',.2f')} bi"


def fmt_pct(val: float) -> str:
    """+1,2%"""
    return f"{_br(val, '+.1f')}%"


def fmt_ratio(val: float) -> str:
    """Sinistralidade ou qualquer ratio: 65,3%"""
    return f"{val:.1f}%".replace(".", ",")


def fmt_pp(val: float) -> str:
    """Variação em pontos percentuais: +1,2 p.p."""
    return f"{val:+.1f}".replace(".", ",") + " p.p."
