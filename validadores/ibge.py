"""
Validação dos indicadores de fonte IBGE
=========================================
1. Coleta todas as séries via API SIDRA/IBGE.
2. Combina em DataFrame largo (Ano | Mês | indicador1 | indicador2 | ...).
3. Compara com a exportação do Cognos e gera relatório de divergências.

Arquivo Cognos esperado  : cognos/exportacao_cognos.xlsx  (aba "ibge")
Dados API gerados        : outputs/ibge/dados_api.xlsx
Relatório de divergências: outputs/divergencias/divergencias_ibge.xlsx
"""

import os
import sys
import warnings

import pandas as pd

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_utils import (
    pega_sidra, processa_sidra,
    combina_indicadores, analisa_divergencias,
    verifica_atualizacao, salva_relatorio, carrega_cognos,
)

#  Caminhos
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEITURA_IBGE  = os.path.join(BASE_DIR, 'data', 'descontinuadas', 'IBGE') + '/'
COGNOS_FILE   = os.path.join(BASE_DIR, 'data', 'cognos', 'Indicadores IBGE.xlsx')
COGNOS_SHEET  = 'Página1_1'    # nome da aba no arquivo Cognos
OUTPUT_API    = os.path.join(BASE_DIR, 'outputs', 'dados', 'dados_api_ibge.xlsx')
OUTPUT_REPORT = os.path.join(BASE_DIR, 'outputs', 'divergencias', 'divergencias_ibge.xlsx')

#  Indicadores padrão (endpoint SIDRA -> nome da coluna) 
INDICADORES = {
    '/t/6390/n1/all/v/5933/p/all':                                          'Renda real per capita',
    '/t/6390/n1/all/v/5929/p/all':                                          'Renda nominal per capita',
    '/t/6381/n1/all/v/4099/p/all/d/v4099%201':                             'Taxa de desemprego',
    '/t/6320/n1/all/v/4090/p/all/c11913/96165':                            'População Ocupada (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/31722':                            'População Ocupada com Carteira (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/31723':                            'População Ocupada sem Carteira (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/31724':                            'População Ocupada como Trabalhador Doméstico (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/31727':                            'População Ocupada no Setor Público (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/96170':                            'População Ocupada como Empregador (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/96171':                            'População Ocupada como Conta-Própria (Mil pessoas)',
    '/t/6320/n1/all/v/4090/p/all/c11913/31731':                            'População Ocupada Trabalhador familiar auxiliar (Mil pessoas)',
    '/t/8887/n1/all/v/12606/p/all/c543/129285/d/v12606%205':               'Produção de alimentos - índice',
}


# Coleta

def coleta_dados() -> pd.DataFrame | None:
    """Coleta todos os indicadores IBGE e retorna DataFrame largo."""
    frames: list[pd.DataFrame] = []

    # Indicadores padrão
    for endpoint, nome in INDICADORES.items():
        print(f'  Coletando: {nome}')
        raw = pega_sidra(endpoint)
        df  = processa_sidra(raw)
        if df is None:
            print(f'    ✗ Falha: {nome}')
            continue
        df.columns = ['data', nome]
        frames.append(df)

    #  Indicador especial: População Ocupada Trabalhador Informal
    # Soma de categorias específicas a partir de dez/2015 + histórico (NAO APAGAR)
    nome_informal = 'População Ocupada Trabalhador Informal (Mil pessoas)'
    print(f'  Coletando: {nome_informal}')
    try:
        raw = pega_sidra('/t/6320/n1/all/v/4090/p/all/c11913/31723,31726,31729,31731,45935,45937')
        df  = processa_sidra(raw)
        if df is not None:
            df = df[df['data'] > '2015-11-01']
            df = df.groupby('data')['V'].sum().reset_index()
            df.columns = ['data', nome_informal]

            arq_aux = LEITURA_IBGE + 'NAO APAGAR - POCTI.csv'
            if os.path.exists(arq_aux):
                aux = pd.read_csv(arq_aux, sep=';')
                aux['data'] = pd.to_datetime(
                    aux['data'].astype(str).str.slice(0, 6), format='%Y%m'
                )
                aux.columns = df.columns
                df = pd.concat([aux, df], ignore_index=True)
            else:
                print(f'    ⚠️️ Arquivo auxiliar não encontrado: {arq_aux}')

            frames.append(df)
    except Exception as e:
        print(f'    ✗ Erro ao coletar {nome_informal}: {e}')

    #  Indicador especial: População Ocupada Trabalhador Formal 
    nome_formal = 'População Ocupada Trabalhador Formal (Mil pessoas)'
    print(f'  Coletando: {nome_formal}')
    try:
        raw = pega_sidra('/t/6320/n1/all/v/4090/p/all/c11913/31722,31725,31728,31730,45934,45936')
        df  = processa_sidra(raw)
        if df is not None:
            df = df[df['data'] > '2015-11-01']
            df = df.groupby('data')['V'].sum().reset_index()
            df.columns = ['data', nome_formal]

            arq_aux = LEITURA_IBGE + 'NAO APAGAR - POCTF.csv'
            if os.path.exists(arq_aux):
                aux = pd.read_csv(arq_aux, sep=';')
                aux['data'] = pd.to_datetime(
                    aux['data'].astype(str).str.slice(0, 6), format='%Y%m'
                )
                aux.columns = df.columns
                df = pd.concat([aux, df], ignore_index=True)
            else:
                print(f'    ⚠️️ Arquivo auxiliar não encontrado: {arq_aux}')

            frames.append(df)
    except Exception as e:
        print(f'    ✗ Erro ao coletar {nome_formal}: {e}')

    return combina_indicadores(frames)


#  Main 

def main() -> None:
    sep = '=' * 60
    print(sep)
    print('VALIDAÇÃO DE INDICADORES — IBGE')
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
        print(f'  ⚠️️ Arquivo Cognos não encontrado em: {COGNOS_FILE}')
        print('  Coloque o arquivo exportado do Cognos na pasta "cognos/" e execute novamente.')
        print('  Os dados da API foram salvos; a validação será realizada na próxima execução.')
        return

    print(f'  ✔️ {len(dados_cognos)} registros carregados')

    # 3. Analisar divergências 
    print('\n[3/3] Analisando divergências...')
    divergencias, resumo = analisa_divergencias(dados_api, dados_cognos)

    atualizacao = verifica_atualizacao(dados_api)
    salva_relatorio(divergencias, resumo, OUTPUT_REPORT, atualizacao)

    # Resumo no console
    n_ok   = int((resumo['Status'].str.startswith('✔️')).sum())
    n_warn = int((resumo['Status'].str.startswith('⚠️')).sum())
    n_divs = len(divergencias)

    print(f'\n{sep}')
    print('RESULTADO — IBGE')
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
