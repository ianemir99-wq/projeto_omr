# Leitor de gabarito (OMR) usando OpenCV
# le a foto de um gabarito de 30 questoes e mostra qual opcao foi marcada em cada uma
#
# uso: python omr.py caminho_da_foto.jpg
#      python omr.py caminho_da_foto.jpg --sem-janela   (so imprime, sem abrir a janela)

import sys

from configuracoes import TOTAL_DE_BOLINHAS, QUANTIDADE_DE_COLUNAS, QUESTOES_POR_COLUNA
from preprocessamento import carregar_imagem, preprocessar_imagem
from deteccao import achar_bolinhas
from leitura import organizar_em_questoes, ler_respostas
from desenho import desenhar_respostas, mostrar_imagem


class GabaritoNaoDetectado(Exception):
    pass


def ler_gabarito(imagem):
    """Le a foto do gabarito e retorna (respostas, questoes).

    Da erro GabaritoNaoDetectado se nao encontrar as 120 bolinhas."""
    imagem_binaria = preprocessar_imagem(imagem)
    bolinhas = achar_bolinhas(imagem_binaria)
    if len(bolinhas) != TOTAL_DE_BOLINHAS:
        raise GabaritoNaoDetectado(f"Encontrei {len(bolinhas)} bolinhas, esperava {TOTAL_DE_BOLINHAS}.")

    questoes = organizar_em_questoes(bolinhas)
    respostas = ler_respostas(imagem_binaria, questoes)
    return respostas, questoes


def main():
    argumentos = sys.argv[1:]
    sem_janela = "--sem-janela" in argumentos
    if sem_janela:
        argumentos.remove("--sem-janela")
    if len(argumentos) == 0:
        print("Uso: python omr.py caminho_da_foto.jpg [--sem-janela]")
        sys.exit(1)

    caminho_da_foto = argumentos[0]
    try:
        imagem = carregar_imagem(caminho_da_foto)
        respostas, questoes = ler_gabarito(imagem)
    except (FileNotFoundError, GabaritoNaoDetectado) as erro:
        print(f"Erro: {erro}")
        sys.exit(1)

    # imprime igual ao gabarito: Q1 Q11 Q21 na mesma linha
    print("Respostas lidas ( - = em branco, * = mais de uma marcada )\n")
    for numero_da_linha in range(QUESTOES_POR_COLUNA):
        texto_da_linha = ""
        for numero_da_coluna in range(QUANTIDADE_DE_COLUNAS):
            indice = numero_da_linha + numero_da_coluna * QUESTOES_POR_COLUNA
            texto_da_linha += f"Q{indice + 1}: {respostas[indice]}\t"
        print(texto_da_linha)

    if not sem_janela:
        imagem_com_resultado = desenhar_respostas(imagem, questoes, respostas)
        mostrar_imagem("Resultado (verde = resposta lida)", imagem_com_resultado)


if __name__ == "__main__":
    main()
