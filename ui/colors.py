"""Paleta de cores CNseg para o dashboard AMseg."""
CNSEG_ORANGE  = "#F7871F"   # brand primary — Arrecadação, Capitalização
CNSEG_ORANGE2 = "#EC6608"   # laranja escuro — Início (nav)
CNSEG_BLUE    = "#3278C2"   # Danos e Responsabilidades, Sinistros
CNSEG_NAVY    = "#1C2024"   # azul quase preto — Sinistros (nav)
CNSEG_TEAL    = "#20A787"   # Previdência Aberta, variação positiva
CNSEG_CYAN    = "#7EBCD8"   # Coberturas de Pessoas
CNSEG_DCCOM   = "#178FC6"   # Despesa de Comercialização (página DC)
CNSEG_DEMONST = "#FFD114"   # Demonstrações Contábeis (página Demonst. Contábil)
CNSEG_YELLOW  = "#FFD114"   # Saúde Suplementar
CNSEG_GRAY    = "#A09FA4"   # Outros / fallback
CNSEG_RED     = "#F44949"   # variação negativa
CNSEG_DARK    = "#403D4A"   # texto escuro / sidebar
CNSEG_BROWN   = "#B1670C"   # Capitalização
CNSEG_IA      = "#B084CC"   # Pergunte à IA (nav)
CNSEG_COB     = "#2C5A52"   # Coberturas de Pessoas (nav)

SEG_COLORS = {
    # Segmentos
    "Danos e Responsabilidades": CNSEG_BLUE,
    "Coberturas de Pessoas":     CNSEG_COB,
    "Capitalização":             CNSEG_BROWN,
    "Saúde Suplementar":         CNSEG_YELLOW,
    "Outros":                    CNSEG_GRAY,

    # Grupos - Coberturas de Pessoas
    "Seguros de Pessoas":        "#612446",   #
    "Planos Tradicionais":       "#7EC8E3",   #
    "Previdência Aberta":        "#5B7FA6",

    # Grupos - Danos e Responsabilidades
    "Automóvel":                 "#2A5FA0",   # 
    "Patrimonial":               "#E07B39",   # 
    "Rural":                     "#6AAB47",   # 
    "Habitacional":              "#C8A800",   # 
    "Responsabilidade Civil":    "#6B3FA8",   # 
    "Transportes":               "#D95F5F",   # 
    "Riscos Financeiros":        "#2196B6",   # 
    "Marítimos e aeronáuticos":  "#00796B",   # 
    "Garantia Estendida":        "#8162F0",   #
    "DPVAT":                     "#B0B0B0",   #
}

GRUPO_COLORS = [
    CNSEG_ORANGE, CNSEG_BLUE, CNSEG_TEAL,
    CNSEG_CYAN, CNSEG_YELLOW, CNSEG_GRAY, CNSEG_DARK,
]

# Cores por Ramo (grupo2) — famílias cromáticas derivadas do grupo1 pai
RAMO_COLORS = {
    # ── Capitalização — família âmbar/marrom (pai: #B1670C) ─────────────────
    "Tradicional":                    "#B1670C",
    "Compra-Programada":              "#D47E10",
    "Popular":                        "#E89830",
    "Incentivo":                      "#F0B050",
    "Filantropia Premiável":          "#C05808",
    "Instrumento de Garantia":        "#8B4F08",
    "Antes Circ 365 e Não Adequado":  "#A09FA4",   # obsoleto → cinza
    "Não Informado":                  "#C8C7CB",

    # ── Previdência Aberta — família teal (pai: #20A787) ────────────────────
    "Família PGBL":                   "#157A61",
    "Família VGBL":                   "#20A787",
    "Microsseguros Previdência":      "#4DC9A0",

    # ── Seguros de Pessoas — família vinho (pai: #612446) ───────────────────
    "Seguro Coletivo":                "#612446",
    "Seguro Individual":              "#8C3460",

    # ── Patrimonial — família laranja queimado (pai: #E07B39) ───────────────
    "Massificados":                   "#E07B39",
    "Grandes Riscos":                 "#B85A20",
    "Risco de Engenharia":            "#F09858",
    "Riscos Diversos":                "#D46030",
    "Demais Coberturas Patrimoniais": "#A09FA4",

    # ── Rural — família verde (pai: #6AAB47) ────────────────────────────────
    "Agrícola":                       "#6AAB47",
    "Pecuário":                       "#4A8A30",
    "Vida do Produtor Rural":         "#8AC860",
    "Benfeitorias e Penhor Rural":    "#9ABB70",
    "Outros Rural":                   "#A09FA4",

    # ── Transportes — família vermelho suave (pai: #D95F5F) ─────────────────
    "Embarcador Nacional":            "#D95F5F",
    "Embarcador Internacional":       "#B03A3A",
    "Transportador":                  "#F08080",

    # ── Riscos Financeiros — família azul oceano (pai: #2196B6) ─────────────
    "Garantia":                       "#2196B6",
    "Crédito":                        "#156E88",
    "Fiança Locatícia":               "#45B8D8",
    "Outros Riscos Financeiros":      "#A09FA4",

    # ── Marítimos e Aeronáuticos — família verde-azulado (pai: #00796B) ─────
    "Marítimos":                      "#00796B",
    "Aeronáuticos":                   "#009E8C",

    # ── Saúde Suplementar — família amarelo (pai: #FFD114) ──────────────────
    "Médico-Hospitalar":              "#FFD114",
    "Odontológico":                   "#F0B800",
    "Não Segregável":                 "#A09FA4",
}

#abreviações para legendas e rótulos
SEG_ABBR = {
    "Danos e Responsabilidades": "Danos e Resp.",
    "Coberturas de Pessoas":     "Cob. Pessoas",
    "Capitalização":             "Cap.",
    "Previdência Aberta":        "Prev. Aberta",
    "Saúde Suplementar":         "Saúde",
}
