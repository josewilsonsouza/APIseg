"""
ui/toc.py
Floating table of contents injected into the parent Streamlit DOM via JS.
Each re-render removes the previous TOC and inserts an updated one.
The panel starts minimized; clique em "Seções" para expandir/recolher.
Estado (aberto/fechado) é persistido em localStorage entre rerenders.
"""

import streamlit.components.v1 as _components

ENABLED  = True # False para ocultar o TOC globalmente

_TOC_ID  = "amseg-floating-toc"
_LS_KEY  = "amseg-toc-open"


def render_toc(sections: list[tuple[str, str]]) -> None:
    """Injeta TOC flutuante colapsável no DOM pai do Streamlit.

    Parameters
    ----------
    sections : list of (label, anchor_id)
        Label visível e ID do <div> âncora renderizado via
        st.markdown('<div id="anchor-id"></div>', unsafe_allow_html=True)
        antes de cada seção.
        Passe [] para remover o TOC sem inserir um novo.
    """
    if not ENABLED or not sections:
        _components.html(
            f'<script>'
            f'var _t=window.parent.document.getElementById("{_TOC_ID}");'
            f'if(_t)_t.remove();'
            f'</script>',
            height=0,
        )
        return

    links_js = ", ".join(f'["{lbl}", "{slug}"]' for lbl, slug in sections)

    script = f"""
    <script>
    (function() {{
        var ID     = '{_TOC_ID}';
        var LS_KEY = '{_LS_KEY}';
        var ORANGE = '#F7871F';
        var SECS   = [{links_js}];
        var doc    = window.parent.document;

        // Remove instância anterior
        var old = doc.getElementById(ID);
        if (old) old.remove();

        // Restaura estado salvo (default: fechado)
        var isOpen = localStorage.getItem(LS_KEY) === 'true';

        // ── Container ───────────────────────────────────────────────────────
        var toc = doc.createElement('div');
        toc.id = ID;
        Object.assign(toc.style, {{
            position:       'fixed',
            top:            '80px',
            right:          '16px',
            zIndex:         '9999',
            background:     'rgba(40,37,47,0.94)',
            border:         '1px solid rgba(247,135,31,0.28)',
            borderRadius:   '8px',
            padding:        '7px 14px 8px',
            display:        'flex',
            flexDirection:  'column',
            gap:            '0px',
            fontSize:       '11px',
            backdropFilter: 'blur(6px)',
            fontFamily:     'sans-serif',
            boxShadow:      '0 2px 14px rgba(0,0,0,0.35)',
            userSelect:     'none',
            lineHeight:     '1.5',
            cursor:         'default',
            minWidth:       '0',
        }});

        // ── Cabeçalho (clicável) ─────────────────────────────────────────────
        var hdr = doc.createElement('div');
        Object.assign(hdr.style, {{
            display:        'flex',
            alignItems:     'center',
            gap:            '6px',
            cursor:         'pointer',
            whiteSpace:     'nowrap',
        }});

        var ttl = doc.createElement('span');
        ttl.textContent = '≡ SEÇÕES';
        Object.assign(ttl.style, {{
            fontSize:      '9.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.09em',
            color:         ORANGE,
            fontWeight:    '700',
        }});

        var arr = doc.createElement('span');
        Object.assign(arr.style, {{
            fontSize:    '9px',
            color:       ORANGE,
            display:     'inline-block',
            transition:  'transform 0.2s',
            transform:   isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
        }});
        arr.textContent = '▶';

        hdr.appendChild(ttl);
        hdr.appendChild(arr);
        toc.appendChild(hdr);

        // ── Painel de links ─────────────────────────────────────────────────
        var panel = doc.createElement('div');
        Object.assign(panel.style, {{
            display:        isOpen ? 'flex' : 'none',
            flexDirection:  'column',
            gap:            '3px',
            marginTop:      '7px',
            minWidth:       '138px',
            overflow:       'hidden',
        }});

        SECS.forEach(function(pair) {{
            var label = pair[0], slug = pair[1];
            var a = doc.createElement('a');
            a.textContent = label;
            a.href = '#';
            Object.assign(a.style, {{
                color:          '#ccc',
                textDecoration: 'none',
                display:        'block',
                padding:        '1px 0',
                cursor:         'pointer',
            }});
            a.addEventListener('mouseover', function() {{ a.style.color = ORANGE; }});
            a.addEventListener('mouseout',  function() {{ a.style.color = '#ccc';  }});
            a.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                var el = doc.getElementById(slug);
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                a.style.color = ORANGE;
                setTimeout(function() {{ a.style.color = '#ccc'; }}, 800);
            }});
            panel.appendChild(a);
        }});

        toc.appendChild(panel);

        // ── Toggle ao clicar no cabeçalho ───────────────────────────────────
        hdr.addEventListener('click', function() {{
            isOpen = !isOpen;
            localStorage.setItem(LS_KEY, isOpen);
            panel.style.display  = isOpen ? 'flex' : 'none';
            arr.style.transform  = isOpen ? 'rotate(90deg)' : 'rotate(0deg)';
        }});

        doc.body.appendChild(toc);
    }})();
    </script>
    """
    _components.html(script, height=0)


def anchor(anchor_id: str) -> None:
    """Renderiza âncora invisível para o TOC navegar até ela."""
    import streamlit as st
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)


def scroll_to_top() -> None:
    """Rola a página ao topo se st.session_state['scroll_to_top'] estiver True.

    Deve ser chamada APÓS o render da página, para que o JS execute
    depois de todo o conteúdo da view estar no DOM.
    """
    import streamlit as st
    if not st.session_state.pop("scroll_to_top", False):
        return
    # Incrementa contador para garantir conteúdo HTML único a cada chamada,
    # evitando que o React/Streamlit cache o componente e não reexecute o JS.
    _cnt = st.session_state.get("_scroll_cnt", 0) + 1
    st.session_state["_scroll_cnt"] = _cnt
    _components.html(
        f"""
        <script>
        /* scroll-{_cnt} */
        function _scrollTop() {{
            var doc = window.parent.document;
            var sel = [
                '[data-testid="stMain"]',
                '[data-testid="stAppViewContainer"]',
                '.main',
            ];
            for (var i = 0; i < sel.length; i++) {{
                var el = doc.querySelector(sel[i]);
                if (el) el.scrollTop = 0;
            }}
            window.parent.scrollTo(0, 0);
        }}
        var _n = 0;
        function _retry() {{ _scrollTop(); if (++_n < 2) setTimeout(_retry, 60); }}
        _retry();
        </script>
        """,
        height=0,
    )
