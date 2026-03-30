"""
Validação dos indicadores de fonte BACEN
=========================================
1. Coleta todas as séries via API do Banco Central do Brasil.
2. Combina em DataFrame largo (Ano | Mês | indicador1 | indicador2 | ...).
3. Compara com a exportação do Cognos e gera relatório de divergências.

Arquivo Cognos esperado : cognos/exportacao_cognos.xlsx  (aba "bacen")
Dados API gerados       : outputs/bacen/dados_api.xlsx
Relatório de divergências: outputs/divergencias/divergencias_bacen.xlsx
"""

import os
import sys
import warnings

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

#  Caminhos
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEITURA_BACEN = os.path.join(BASE_DIR, 'data', 'descontinuadas', 'BACEN') + '/'
COGNOS_FILE   = os.path.join(BASE_DIR, 'data', 'cognos', 'Indicadores BACEN.xlsx')
COGNOS_SHEET  = 'Página1_1'
OUTPUT_API    = os.path.join(BASE_DIR, 'outputs', 'dados', 'dados_api_bacen.xlsx')
OUTPUT_REPORT = os.path.join(BASE_DIR, 'outputs', 'divergencias', 'divergencias_bacen.xlsx')

URL_BCB = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados?formato=json'

# Códigos BCB cujo valor bruto é variação % mensal — precisam de índice encadeado
CODIGOS_ENCADEADOS = {188, 189, 190, 191, 192, 194, 433, 1641, 1650, 7456, 7468, 7470, 7495}

# Indicadores padrão (código BCB -> nome da coluna)
INDICADORES = {
    188:   'INPC índice',
    189:   'IGPM índice',
    190:   'IGPDI índice',
    191:   'IPCBr índice',
    192:   'INCC índice',
    194:   'ICV índice',
    7493:  'Cesta básica',
    433:   'IPCA índice',
    22083: 'PIB agropecuário índice',   # série defasada 2 meses
    1641:  'IPCA saúde índice',
    1650:  'INPC saúde índice',
    1835:  'Depósito de poupança (R$ milhares)',
    3696:  'Câmbio dólar',
    4189:  'SELIC',
    4380:  'PIB (R$ milhões)',
    7384:  'Venda automóvel de passeio',
    7385:  'Venda automóvel comercial leve',
    7456:  'INCC-M índice',
    7468:  'IPC Fipe in natura índice',
    7470:  'IPC Fipe índice',
    7495:  'SINAPI índice',
    7616:  'IRPF',
    20579: 'Crédito consignado (R$ milhões)',
}


# Coleta

def coleta_dados() -> pd.DataFrame | None:
    """Coleta todos os indicadores BACEN e retorna DataFrame largo."""
    frames: list[pd.DataFrame] = []

    # Indicadores padrão
    for codigo, nome in INDICADORES.items():
        print(f'  Coletando: {nome}')
        df = pega_bcb(URL_BCB.format(codigo), nome)
        if df is None:
            continue
        # Garante que a série comece em 2001-01-01 para o cálculo do índice 100 ser correto
        df = df[df['data'] >= '2001-01-01'].sort_values('data').reset_index(drop=True)
        if codigo == 22083:
            # PIB agropecuário: data publicada com 2 meses de defasagem
            df['data'] = df['data'] + pd.DateOffset(months=2)
        if codigo in CODIGOS_ENCADEADOS:
            df = calcula_indice_encadeado(df, nome)
        frames.append(df)

    # Indicador especial: IPCA seguro saúde índice
    print('  Coletando: IPCA seguro saúde índice')
    dfb = pega_bcb(URL_BCB.format(4461), 'IPCA seguro saúde índice')
    if dfb is not None:
        # 1. Garante que começamos em 2001-01-01
        dfb = dfb[dfb['data'] >= '2001-01-01']
        dfb = dfb[dfb['data'] < '2020-01-01']
        
        dfi = processa_sidra(pega_sidra('/t/7060/n1/all/v/63/p/all/c315/7695/d/v63%202'))
        if dfi is not None:
            dfi.columns = dfb.columns
            combined = pd.concat([dfb, dfi], ignore_index=True)
        else:
            combined = dfb
            
        # 2. Agora o primeiro registro (Jan/2001) será o 100.0
        frames.append(calcula_indice_encadeado(combined, 'IPCA seguro saúde índice'))

    # Indicador especial: Saldo crédito rural
    # Soma das séries 20597 + 20609, concatenada com histórico (arquivo auxiliar)
    print('  Coletando: Saldo crédito rural')
    try:
        s1 = pega_bcb(URL_BCB.format(20597), 'v1')
        s2 = pega_bcb(URL_BCB.format(20609), 'v2')
        if s1 is not None and s2 is not None:
            tab = pd.merge(s1, s2, on='data', how='left')
            tab['Saldo crédito rural'] = tab['v1'] + tab['v2']
            tab = tab[['data', 'Saldo crédito rural']]

            arq_aux = LEITURA_BACEN + 'NAO APAGAR - 2048.csv'
            if os.path.exists(arq_aux):
                aux = pd.read_csv(arq_aux, sep=';', decimal=',').iloc[:, :2]
                aux.columns = tab.columns
                aux['data'] = pd.to_datetime(aux['data'], format='%d/%m/%Y')
                tab = pd.concat([aux, tab], ignore_index=True)
            else:
                print(f'    ⚠️️ Arquivo auxiliar não encontrado: {arq_aux}')

            frames.append(tab)
    except Exception as e:
        print(f'    ✗ Erro ao coletar Saldo crédito rural: {e}')

    return combina_indicadores(frames)


# Main

def main() -> None:
    sep = '=' * 60
    print(sep)
    print('VALIDAÇÃO DE INDICADORES — BACEN')
    print(sep)

    os.makedirs(os.path.dirname(OUTPUT_API),    exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_REPORT), exist_ok=True)
    os.makedirs(os.path.dirname(COGNOS_FILE),   exist_ok=True)

    # 1. Coletar dados da API
    print('\n[1/3] Coletando dados das APIs...')
    dados_api = coleta_dados()

    if dados_api is None or dados_api.empty:
        print('Erro crítico: nenhum dado coletado via API.')
        return

    dados_api.to_excel(OUTPUT_API, index=False)
    print(f'  ✔️ {len(dados_api)} períodos × {len(dados_api.columns) - 2} indicadores → {OUTPUT_API}')

    # 2. Carregar exportação do Cognos
    print('\n[2/3] Carregando exportação do Cognos...')
    dados_cognos = carrega_cognos(COGNOS_FILE, COGNOS_SHEET)

    if dados_cognos is None:
        print(f'  ⚠️️️ Arquivo Cognos não encontrado em: {COGNOS_FILE}')
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
    n_warn = int((resumo['Status'].str.startswith('⚠️️')).sum())
    n_divs = len(divergencias)

    print(f'\n{sep}')
    print('RESULTADO — BACEN')
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
