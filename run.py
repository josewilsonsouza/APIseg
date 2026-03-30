"""
Runner master — executa a validação para todas as fontes.

Uso:
    python run.py            # roda bacen + ibge + ipea
    python run.py bacen      # roda somente BACEN
    python run.py ibge ipea  # roda IBGE e IPEA
"""

import sys


def main() -> None:
    fontes_disponiveis = ('bacen', 'ibge', 'ipea')

    args = [a.lower() for a in sys.argv[1:]]
    fontes = args if args else list(fontes_disponiveis)

    invalidas = [f for f in fontes if f not in fontes_disponiveis]
    if invalidas:
        print(f'Fonte(s) desconhecida(s): {invalidas}')
        print(f'Opções válidas: {fontes_disponiveis}')
        sys.exit(1)

    for fonte in fontes:
        if fonte == 'bacen':
            from validadores.bacen import main as run
        elif fonte == 'ibge':
            from validadores.ibge import main as run
        elif fonte == 'ipea':
            from validadores.ipea import main as run

        print()
        run()

    print('\nConcluído.')


if __name__ == '__main__':
    main()
