"""
Utilitários compartilhados entre os scripts de validação de indicadores.
"""

import re
import time
import warnings
import pandas as pd
import requests

warnings.filterwarnings('ignore')


def _normaliza_numero(x: str) -> str:
    """
    Converte string numérica para formato float compatível com pd.to_numeric.

    Casos tratados:
      "1.234,56"  → "1234.56"   (padrão BR com decimal)
      "1.234"     → "1234"      (inteiro BR com milhar, sem decimal)
      "1.234.567" → "1234567"   (inteiro BR com múltiplos milhares)
      "1.5"       → "1.5"       (ponto como decimal — mantém)
      "1234"      → "1234"      (sem separadores — mantém)
    """
    x = re.sub(r'\s', '', x)
    if ',' in x:
        return x.replace('.', '').replace(',', '.')
    if re.match(r'^\d{1,3}(\.\d{3})+$', x):
        return x.replace('.', '')
    return x


# Coleta de dados

def pega_bcb(url: str, nome: str, max_tentativas: int = 3) -> pd.DataFrame | None:
    """Consulta a API do Banco Central e retorna DataFrame com colunas [data, nome]."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            df = pd.DataFrame(resp.json())
            df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
            df = df[df['data'] >= '2001-01-01'].copy()
            df.columns = ['data', nome]
            df[nome] = pd.to_numeric(df[nome], errors='coerce')
            return df
        except requests.RequestException as e:
            print(f'    Tentativa {tentativa}/{max_tentativas} – erro de requisição ({nome}): {e}')
            if tentativa < max_tentativas:
                time.sleep(2)
        except Exception as e:
            print(f'    Erro inesperado ({nome}): {e}')
            break
    print(f'    ❌ Falha definitiva ao coletar: {nome}')
    return None


def pega_sidra(api: str) -> pd.DataFrame | None:
    """Consulta a API SIDRA/IBGE e retorna DataFrame bruto."""
    url = f'https://apisidra.ibge.gov.br/values{api}'
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['V'] = pd.to_numeric(df['V'], errors='coerce')
        return df
    except Exception as e:
        print(f'    ❌ Erro SIDRA ({api}): {e}')
        return None


def processa_sidra(tabela: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Converte DataFrame SIDRA bruto para [data, V].
    Trata tanto períodos mensais quanto trimestrais.
    """
    if tabela is None or tabela.empty:
        return None
    try:
        ano = tabela['D3C'].str.slice(0, 4)
        if tabela['D3N'].str.contains('trimestre', case=False).iloc[0]:
            mes = tabela['D3C'].apply(lambda x: str(int(x[4:]) * 3).zfill(2))
        else:
            mes = tabela['D3C'].str.slice(4,)
        tabela = tabela.copy()
        tabela['data'] = pd.to_datetime(ano + mes, format='%Y%m')
        return tabela[['data', 'V']].copy()
    except Exception as e:
        print(f'    ❌ Erro ao processar tabela SIDRA: {e}')
        return None


def calcula_indice_encadeado(df: pd.DataFrame, col: str, base_valor: float = 100.0) -> pd.DataFrame:
    """
    Converte variação percentual mensal em índice acumulado encadeado.

    O primeiro ponto da série (jan/2001) recebe base_valor. Cada mês seguinte aplica:
        I_t = I_{t-1} × (1 + r_t / 100)

    Valores ausentes no meio da série carregam o índice do período anterior.
    """
    df = df.sort_values('data').reset_index(drop=True).copy()
    df[col] = pd.to_numeric(df[col], errors='coerce')
    valores = df[col].tolist()
    resultado = [base_valor]
    for r in valores[1:]:
        resultado.append(resultado[-1] if pd.isna(r) else resultado[-1] * (1 + r / 100))
    df[col] = resultado
    return df


# Combinação

def combina_indicadores(frames: list[pd.DataFrame]) -> pd.DataFrame | None:
    """
    Recebe lista de DataFrames com colunas [data, <indicador>] e retorna
    DataFrame largo com colunas [Ano, Mês, ind1, ind2, ...].
    """
    combined = None
    for df in frames:
        if df is None or df.empty:
            continue
        df = df.copy()
        df['Ano'] = df['data'].dt.year
        df['Mês'] = df['data'].dt.month
        df = df.drop(columns='data')
        if combined is None:
            combined = df
        else:
            combined = pd.merge(combined, df, on=['Ano', 'Mês'], how='outer')

    if combined is None or combined.empty:
        return None

    combined = combined.sort_values(['Ano', 'Mês']).reset_index(drop=True)
    cols = ['Ano', 'Mês'] + [c for c in combined.columns if c not in ('Ano', 'Mês')]
    return combined[cols]


# Análise de divergências

def analisa_divergencias(
    dados_api: pd.DataFrame,
    dados_cognos: pd.DataFrame,
    tolerancia_pct: float = 0.01,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compara dois DataFrames (ambos com colunas Ano, Mês, indicadores).

    Parâmetros
    ----------
    dados_api      : dados coletados via API
    dados_cognos   : dados exportados do Cognos
    tolerancia_pct : diferença relativa (%) mínima para considerar divergência

    Retorna
    -------
    (divergencias_df, resumo_df)
    """
    indicadores = [c for c in dados_api.columns if c not in ('Ano', 'Mês')]

    # Merge externo para detectar períodos ausentes de cada lado
    merged = pd.merge(
        dados_api,
        dados_cognos,
        on=['Ano', 'Mês'],
        how='outer',
        suffixes=('_api', '_cognos'),
    )

    all_divs: list[pd.DataFrame] = []
    resumo_rows: list[dict] = []

    cols_cognos_presentes = set(dados_cognos.columns) - {'Ano', 'Mês'}

    for ind in indicadores:
        # Após merge com suffixes, o nome da coluna depende se existia nos dois DFs
        col_api    = f'{ind}_api'    if f'{ind}_api'    in merged.columns else ind
        col_cognos = f'{ind}_cognos' if f'{ind}_cognos' in merged.columns else None

        # Indicador ausente completamente no Cognos
        if col_cognos is None or col_cognos not in merged.columns:
            n_api = int(dados_api[ind].notna().sum()) if ind in dados_api.columns else 0
            resumo_rows.append({
                'Indicador':        ind,
                'Registros API':    n_api,
                'Registros Cognos': 0,
                'Coincidentes':     0,
                'Divergências':     'N/A',
                'Status':           '⚠️ Indicador ausente no arquivo Cognos',
            })
            continue

        sub = merged[['Ano', 'Mês', col_api, col_cognos]].copy()
        sub.columns = ['Ano', 'Mês', 'v_api', 'v_cognos']
        sub['v_api']    = pd.to_numeric(sub['v_api'],    errors='coerce')
        sub['v_cognos'] = pd.to_numeric(sub['v_cognos'], errors='coerce')

        # Remove linhas onde ambos são nulos (sem informação para comparar)
        sub = sub[~(sub['v_api'].isna() & sub['v_cognos'].isna())]

        mask_api_null    = sub['v_api'].isna()  & sub['v_cognos'].notna()
        mask_cognos_null = sub['v_api'].notna() & sub['v_cognos'].isna()
        mask_ambos       = sub['v_api'].notna() & sub['v_cognos'].notna()

        # Diferença para linhas com valores em ambos os lados
        ambos = sub[mask_ambos].copy()
        ambos['diff_abs'] = (ambos['v_api'] - ambos['v_cognos']).abs()
        denom = ambos['v_cognos'].abs().replace(0, float('nan'))
        ambos['diff_rel'] = (ambos['diff_abs'] / denom * 100).fillna(
            (ambos['diff_abs'] > 0).astype(float) * float('inf')
        )

        divergentes  = ambos[ambos['diff_rel'] >  tolerancia_pct]
        coincidentes = ambos[ambos['diff_rel'] <= tolerancia_pct]

        n_api_null    = int(mask_api_null.sum())
        n_cognos_null = int(mask_cognos_null.sum())
        n_div_val     = len(divergentes)
        n_total       = n_api_null + n_cognos_null + n_div_val

        # Registros ausentes na API
        if n_api_null:
            d = sub[mask_api_null][['Ano', 'Mês', 'v_api', 'v_cognos']].copy()
            d.columns = ['Ano', 'Mês', 'Valor API', 'Valor Cognos']
            d['Indicador']              = ind
            d['Diferença Absoluta']     = None
            d['Diferença Relativa (%)'] = None
            d['Tipo']                   = 'Período ausente na API'
            all_divs.append(d)

        # Registros ausentes no Cognos
        if n_cognos_null:
            d = sub[mask_cognos_null][['Ano', 'Mês', 'v_api', 'v_cognos']].copy()
            d.columns = ['Ano', 'Mês', 'Valor API', 'Valor Cognos']
            d['Indicador']              = ind
            d['Diferença Absoluta']     = None
            d['Diferença Relativa (%)'] = None
            d['Tipo']                   = 'Período ausente no Cognos'
            all_divs.append(d)

        # Valores diferentes
        if n_div_val:
            d = divergentes[['Ano', 'Mês', 'v_api', 'v_cognos', 'diff_abs', 'diff_rel']].copy()
            d.columns = ['Ano', 'Mês', 'Valor API', 'Valor Cognos',
                         'Diferença Absoluta', 'Diferença Relativa (%)']
            d['Indicador'] = ind
            d['Tipo']      = 'Valores diferentes'
            all_divs.append(d)

        n_reg_api    = int(dados_api[ind].notna().sum())    if ind in dados_api.columns    else 0
        n_reg_cognos = int(dados_cognos[ind].notna().sum()) if ind in dados_cognos.columns else 0

        resumo_rows.append({
            'Indicador':        ind,
            'Registros API':    n_reg_api,
            'Registros Cognos': n_reg_cognos,
            'Coincidentes':     len(coincidentes),
            'Divergências':     n_total,
            'Status':           '✔️ OK' if n_total == 0 else f'❌ {n_total} divergência(s)',
        })

    # Verifica indicadores no Cognos que não estão na API
    inds_so_cognos = cols_cognos_presentes - set(indicadores)
    for ind in sorted(inds_so_cognos):
        resumo_rows.append({
            'Indicador':        ind,
            'Registros API':    0,
            'Registros Cognos': int(dados_cognos[ind].notna().sum()),
            'Coincidentes':     0,
            'Divergências':     'N/A',
            'Status':           '⚠️ Indicador no Cognos não gerado pela API',
        })

    COLS_DIV = ['Indicador', 'Ano', 'Mês', 'Valor API', 'Valor Cognos',
                'Diferença Absoluta', 'Diferença Relativa (%)', 'Tipo']

    if all_divs:
        divs_df = (pd.concat(all_divs, ignore_index=True)
                   .reindex(columns=COLS_DIV)
                   .sort_values(['Indicador', 'Ano', 'Mês'])
                   .reset_index(drop=True))
    else:
        divs_df = pd.DataFrame(columns=COLS_DIV)

    resumo_df = pd.DataFrame(resumo_rows)
    return divs_df, resumo_df


# Saída

def _nome_aba(nome: str) -> str:
    """Sanitiza e trunca o nome para uso como aba do Excel (max 31 chars)."""
    for ch in ('\\', '/', '*', '?', '[', ']', ':'):
        nome = nome.replace(ch, '_')
    return nome[:28] + '...' if len(nome) > 31 else nome


def verifica_atualizacao(
    dados_api: pd.DataFrame,
    threshold_mensal: int = 4,
    threshold_trimestral: int = 6,
) -> pd.DataFrame:
    """
    Verifica a última data disponível de cada série e sinaliza possíveis descontinuações.

    Parâmetros
    ----------
    dados_api             : DataFrame largo com colunas [Ano, Mês, indicadores]
    threshold_mensal      : meses sem atualização para séries mensais (padrão: 4)
    threshold_trimestral  : meses sem atualização para séries trimestrais (padrão: 6)

    Retorna
    -------
    DataFrame com colunas:
        Indicador | Último Ano | Último Mês | Meses sem atualização | Periodicidade | Status
    """
    from datetime import date

    hoje = date.today()
    indicadores = [c for c in dados_api.columns if c not in ('Ano', 'Mês')]
    rows = []

    for ind in indicadores:
        sub = dados_api[dados_api[ind].notna()][['Ano', 'Mês']]
        if sub.empty:
            rows.append({
                'Indicador':             ind,
                'Último Ano':            None,
                'Último Mês':            None,
                'Meses sem atualização': None,
                'Periodicidade':         'desconhecida',
                'Status':                '⚠️ Sem dados na API',
            })
            continue

        ultimo_ano = int(sub['Ano'].max())
        ultimo_mes = int(sub.loc[sub['Ano'] == sub['Ano'].max(), 'Mês'].max())

        # Meses sem atualização
        meses_decorridos = (hoje.year - ultimo_ano) * 12 + (hoje.month - ultimo_mes)

        # Detecta periodicidade: se os meses disponíveis são múltiplos de 3 → trimestral
        meses_unicos = sorted(dados_api['Mês'].unique())
        e_trimestral = all(m % 3 == 0 for m in meses_unicos) and len(meses_unicos) <= 4
        periodicidade = 'trimestral' if e_trimestral else 'mensal'
        threshold = threshold_trimestral if e_trimestral else threshold_mensal

        if meses_decorridos > threshold:
            status = f'🔴 Possível descontinuação ({meses_decorridos} meses sem atualização)'
        else:
            status = f'✔️ Atualizada ({meses_decorridos} mês(es) de defasagem)'

        rows.append({
            'Indicador':             ind,
            'Último Ano':            ultimo_ano,
            'Último Mês':            ultimo_mes,
            'Meses sem atualização': meses_decorridos,
            'Periodicidade':         periodicidade,
            'Status':                status,
        })

    return pd.DataFrame(rows)


def salva_relatorio(
    divergencias: pd.DataFrame,
    resumo: pd.DataFrame,
    caminho: str,
    atualizacao: pd.DataFrame | None = None,
) -> None:
    """Salva relatório de divergências em Excel com múltiplas abas."""
    import os
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        resumo.to_excel(writer, sheet_name='Resumo', index=False)
        if atualizacao is not None and not atualizacao.empty:
            atualizacao.to_excel(writer, sheet_name='Atualização séries', index=False)
        if not divergencias.empty:
            divergencias.to_excel(writer, sheet_name='Todas as divergências', index=False)
            for ind in divergencias['Indicador'].unique():
                sub = divergencias[divergencias['Indicador'] == ind]
                sub.to_excel(writer, sheet_name=_nome_aba(ind), index=False)


def carrega_cognos(
    caminho: str,
    nome_aba: str | int = 0,
) -> pd.DataFrame | None:
    """
    Lê o arquivo Cognos e normaliza para o formato [Ano, Mês, indicadores].

    Tenta ler a aba `nome_aba`; se não existir, usa a primeira aba.
    Converte colunas numéricas com separador decimal vírgula (padrão BR).
    """
    import os
    if not os.path.exists(caminho):
        return None

    try:
        try:
            df = pd.read_excel(caminho, sheet_name=nome_aba)
        except Exception:
            df = pd.read_excel(caminho, sheet_name=0)
            print(f'    ⚠️ Aba "{nome_aba}" não encontrada — usando primeira aba.')

        # Normaliza valores numéricos com segurança (Padrão Brasileiro)
        for col in df.columns:
            if col in ('Ano', 'Mês', 'data'):
                continue
            
            # Se já for número nativo do Excel, não mexe para não estragar decimais
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
                
            # Se for texto, limpa seguindo a lógica de milhar/decimal
            df[col] = pd.to_numeric(
                df[col].astype(str).apply(_normaliza_numero),
                errors='coerce',
            )        # Garante colunas Ano e Mês
        # Garante colunas Ano e Mês
        if 'Ano' in df.columns and 'Mês' in df.columns:
            # Dicionário para converter nome do mês em número
            meses_map = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            
            # Se o mês for texto (ex: "janeiro de 2001"), extrai a primeira palavra e mapeia
            if df['Mês'].dtype == 'object':
                df['Mês'] = (df['Mês'].str.lower()
                             .str.split()
                             .str[0]
                             .map(meses_map))
        
        elif 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'], errors='coerce')
            df['Ano']  = df['data'].dt.year
            df['Mês']  = df['data'].dt.month
        else:
            print('    ❌ Cognos não possui colunas "Ano"/"Mês" nem "data".')
            return None

        # Converte para numérico final
        df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').astype('Int64')
        df['Mês'] = pd.to_numeric(df['Mês'], errors='coerce').astype('Int64')
        return df

    except Exception as e:
        print(f'    ❌ Erro ao carregar Cognos: {e}')
        return None
