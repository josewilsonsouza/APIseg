"""
Validação dos indicadores de fonte IPEA
=========================================
Série IPEA reúne indicadores coletados de múltiplas APIs:
  - Banco Central (BCB/SGS)
  - IBGE/SIDRA
  - MDIC/ComexStat (Exportações)

1. Coleta todas as séries via APIs.
2. Combina em DataFrame largo (Ano | Mês | indicador1 | indicador2 | ...).
3. Compara com a exportação do Cognos e gera relatório de divergências.

Arquivo Cognos esperado  : cognos/exportacao_cognos.xlsx  (aba "ipea")
Dados API gerados        : outputs/ipea/dados_api.xlsx
Relatório de divergências: outputs/divergencias/divergencias_ipea.xlsx
"""

import os
import sys
import warnings
from datetime import datetime

import pandas as pd
import requests

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_utils import (
    pega_bcb, pega_sidra, processa_sidra,
    calcula_indice_encadeado,
    combina_indicadores, analisa_divergencias,
    verifica_atualizacao, salva_relatorio, carrega_cognos,
)

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COGNOS_FILE   = os.path.join(BASE_DIR, 'data', 'cognos', 'Indicadores IPEA.xlsx')
COGNOS_SHEET  = 'Página1_1'    # nome da aba no arquivo Cognos
OUTPUT_API    = os.path.join(BASE_DIR, 'outputs', 'dados', 'dados_api_ipea.xlsx')
OUTPUT_REPORT = os.path.join(BASE_DIR, 'outputs', 'divergencias', 'divergencias_ipea.xlsx')

URL_BCB = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados?formato=json'

# ── Indicadores via BCB/SGS (código → nome da coluna) ────────────────────────
INDICADORES_BCB = {
    1374:  'Produção automóveis',
    20541: 'Saldo de crédito pessoas físicas',
    7828:  'Rendimento nominal poupança - índice',
    7628:  'IPI automóveis',
}

# Códigos BCB cujo valor bruto é variação % mensal — precisam de índice encadeado
CODIGOS_ENCADEADOS = {7828}

# Códigos BCB cujo valor da API precisa ser multiplicado por 1.000.000
CODIGOS_ESCALA_M = {7628}

# ── Indicadores via IBGE/SIDRA (endpoint → nome da coluna) ───────────────────
# Endpoints SIDRA cujo valor da API precisa ser multiplicado por 1.000.000
SIDRA_ESCALA_M = {
    '/t/2072/n1/all/v/940/p/all',                          # Poupança nacional bruta
    '/t/1846/n1/all/v/all/p/all/c11255/90691/d/v585%200',  # PIB indústria
}

INDICADORES_SIDRA = {
    '/t/2072/n1/all/v/940/p/all':                                           'Poupança nacional bruta',
    '/t/1620/n1/all/v/all/p/all/c11255/90694/d/v583%202':                  'PIB construção civil índice',
    '/t/8888/n1/all/v/12606/p/all/c544/129314/d/v12606%205':               'Produção industrial média índice',
    '/t/1846/n1/all/v/all/p/all/c11255/90691/d/v585%200':                  'PIB indústria',
    '/t/8757/n1/all/v/7169/p/all/c11046/56731/d/v7169%205':                'Vendas materiais construção - índice',
    '/t/8882/n1/all/v/7169/p/all/c11046/56733/c85/2759/d/v7169%205':       'Vendas nominais de móveis e eletrodomésticos - índice',
    '/t/8886/n1/all/v/12606/p/all/d/v12606%205':                           'Insumos construção civil - índice',
}

# ── URL da API ComexStat (Exportações MDIC) ───────────────────────────────────
COMEX_URL_TPL = (
    'https://api-comexstat.mdic.gov.br/general'
    '?filter=%7B%22yearStart%22:%222001%22,%22yearEnd%22:%22{ano}%22,'
    '%22typeForm%22:1,%22typeOrder%22:2,%22filterList%22:%5B%5D,'
    '%22filterArray%22:%5B%5D,%22rangeFilter%22:%5B%5D,'
    '%22detailDatabase%22:%5B%5D,%22monthDetail%22:true,'
    '%22metricFOB%22:true,%22metricKG%22:false,'
    '%22metricStatistic%22:false,%22metricFreight%22:false,'
    '%22metricInsurance%22:false,%22metricCIF%22:false,'
    '%22monthStart%22:%2201%22,%22monthEnd%22:%2212%22,'
    '%22formQueue%22:%22general%22,%22langDefault%22:%22pt%22,'
    '%22monthStartName%22:%22Janeiro%22,%22monthEndName%22:%22Dezembro%22%7D'
)
NOME_EXPORTACOES = 'Exportações'


# ── Coleta ────────────────────────────────────────────────────────────────────

def coleta_dados() -> pd.DataFrame | None:
    """Coleta todos os indicadores IPEA e retorna DataFrame largo."""
    frames: list[pd.DataFrame] = []

    # Indicadores via BCB
    for codigo, nome in INDICADORES_BCB.items():
        print(f'  Coletando: {nome}')
        df = pega_bcb(URL_BCB.format(codigo), nome)
        if df is None:
            print(f'    ✗ Falha: {nome}')
            continue
        if codigo in CODIGOS_ENCADEADOS:
            df = calcula_indice_encadeado(df, nome)
        if codigo in CODIGOS_ESCALA_M:
            df[nome] = df[nome] * 1_000_000
        frames.append(df)

    # Indicadores via IBGE/SIDRA
    for endpoint, nome in INDICADORES_SIDRA.items():
        print(f'  Coletando: {nome}')
        raw = pega_sidra(endpoint)
        df  = processa_sidra(raw)
        if df is None:
            print(f'    ✗ Falha: {nome}')
            continue
        df.columns = ['data', nome]
        df = df[df['data'] >= '2001-01-01']
        if endpoint in SIDRA_ESCALA_M:
            df[nome] = df[nome] * 1_000_000
        frames.append(df)

    # Exportações (MDIC/ComexStat)
    print(f'  Coletando: {NOME_EXPORTACOES}')
    try:
        url = COMEX_URL_TPL.format(ano=datetime.now().year)
        resp = requests.get(url, verify=False, timeout=60)
        if resp.status_code == 200:
            data_list = resp.json()['data']['list']
            df = pd.DataFrame(data_list)
            df['data'] = pd.to_datetime(
                df.apply(lambda r: f"{r['coAno']}{r['coMes']}", axis=1),
                format='%Y%m',
            )
            df = (df[['data', 'vlFob']]
                    .rename(columns={'vlFob': NOME_EXPORTACOES})
                    .sort_values('data')
                    .reset_index(drop=True))
            frames.append(df)
        else:
            print(f'    ✗ Erro HTTP {resp.status_code} ao consultar ComexStat')
    except Exception as e:
        print(f'    ✗ Erro ao coletar Exportações: {e}')

    return combina_indicadores(frames)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    sep = '=' * 60
    print(sep)
    print('VALIDAÇÃO DE INDICADORES — IPEA')
    print(sep)

    os.makedirs(os.path.dirname(OUTPUT_API),    exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_REPORT), exist_ok=True)
    os.makedirs(os.path.dirname(COGNOS_FILE),   exist_ok=True)

    # 1. Coletar dados da API ──────────────────────────────────────────────────
    print('\n[1/3] Coletando dados das APIs...')
    dados_api = coleta_dados()

    if dados_api is None or dados_api.empty:
        print('Erro crítico: nenhum dado coletado via API.')
        return

    dados_api.to_excel(OUTPUT_API, index=False)
    print(f'  ✔️ {len(dados_api)} períodos × {len(dados_api.columns) - 2} indicadores → {OUTPUT_API}')

    # 2. Carregar exportação do Cognos ────────────────────────────────────────
    print('\n[2/3] Carregando exportação do Cognos...')
    dados_cognos = carrega_cognos(COGNOS_FILE, COGNOS_SHEET)

    if dados_cognos is None:
        print(f'  ⚠️ Arquivo Cognos não encontrado em: {COGNOS_FILE}')
        print('  Coloque o arquivo exportado do Cognos na pasta "cognos/" e execute novamente.')
        print('  Os dados da API foram salvos; a validação será realizada na próxima execução.')
        return

    print(f'  ✔️ {len(dados_cognos)} registros carregados')

    # 3. Analisar divergências ────────────────────────────────────────────────
    print('\n[3/3] Analisando divergências...')
    divergencias, resumo = analisa_divergencias(dados_api, dados_cognos)

    atualizacao = verifica_atualizacao(dados_api)
    salva_relatorio(divergencias, resumo, OUTPUT_REPORT, atualizacao)

    # Resumo no console
    n_ok   = int((resumo['Status'].str.startswith('✔️')).sum())
    n_warn = int((resumo['Status'].str.startswith('⚠')).sum())
    n_divs = len(divergencias)

    print(f'\n{sep}')
    print('RESULTADO — IPEA')
    print(f'  Indicadores OK          : {n_ok}/{len(resumo)}')
    print(f'  Avisos (ausentes/extras): {n_warn}')
    print(f'  Total de divergências   : {n_divs}')

    problemas = resumo[~resumo['Status'].str.startswith('✔️')]
    if not problemas.empty:
        print('\n  Detalhamento:')
        for _, row in problemas.iterrows():
            print(f'    • {row["Indicador"]}: {row["Status"]}')

    print(f'\n  Relatório salvo em: {OUTPUT_REPORT}')
    print(sep)


if __name__ == '__main__':
    main()
