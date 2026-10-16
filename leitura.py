import cv2
import numpy as np

from configuracoes import (QUANTIDADE_DE_COLUNAS, QUESTOES_POR_COLUNA, BOLINHAS_POR_COLUNA, OPCOES,
                           EM_BRANCO, MAIS_DE_UMA_MARCADA, LIMITE_PREENCHIMENTO, MARGEM_DO_RAIO)


def organizar_em_questoes(bolinhas):
    # as bolinhas vem fora de ordem, entao:
    # 1. ordeno pelo x e separo de 40 em 40 (cada coluna do gabarito)
    # 2. dentro da coluna ordeno pelo y e separo de 4 em 4 (cada questao)
    # 3. em cada questao ordeno pelo x de novo pra ficar A, B, C, D
    # TODO: corrigir a perspectiva antes, foto muito torta embaralha as questoes
    quantidade_de_opcoes = len(OPCOES)
    bolinhas = sorted(bolinhas, key=lambda bolinha: bolinha[0])

    questoes = []
    for numero_da_coluna in range(QUANTIDADE_DE_COLUNAS):
        inicio_da_coluna = numero_da_coluna * BOLINHAS_POR_COLUNA
        coluna = bolinhas[inicio_da_coluna:inicio_da_coluna + BOLINHAS_POR_COLUNA]
        coluna = sorted(coluna, key=lambda bolinha: bolinha[1])

        for numero_da_linha in range(QUESTOES_POR_COLUNA):
            inicio_da_questao = numero_da_linha * quantidade_de_opcoes
            opcoes = coluna[inicio_da_questao:inicio_da_questao + quantidade_de_opcoes]
            questoes.append(sorted(opcoes, key=lambda bolinha: bolinha[0]))
    return questoes


def calcular_preenchimento(imagem_binaria, bolinha):
    """Retorna quanto da bolinha esta pintado, de 0 (vazia) ate 1 (toda pintada)."""
    x, y, largura, altura = bolinha
    raio = max(min(largura, altura) // 2 - MARGEM_DO_RAIO, 1)

    # recorta so a bolinha (o max e pra nao dar indice negativo)
    inicio_x = max(x, 0)
    inicio_y = max(y, 0)
    recorte = imagem_binaria[inicio_y:y + altura, inicio_x:x + largura]

    # mascara com um circulo no meio da bolinha, pra contar so os pixels de dentro
    mascara = np.zeros_like(recorte)
    centro = (x + largura // 2 - inicio_x, y + altura // 2 - inicio_y)
    cv2.circle(mascara, centro, raio, 255, -1)

    pixels_do_circulo = cv2.countNonZero(mascara)
    if pixels_do_circulo == 0:
        return 0.0
    pixels_pintados = cv2.countNonZero(cv2.bitwise_and(recorte, recorte, mask=mascara))
    return pixels_pintados / pixels_do_circulo


def ler_respostas(imagem_binaria, questoes):
    respostas = []
    for opcoes in questoes:
        marcadas = []
        for indice_opcao in range(len(opcoes)):
            if calcular_preenchimento(imagem_binaria, opcoes[indice_opcao]) >= LIMITE_PREENCHIMENTO:
                marcadas.append(indice_opcao)

        if len(marcadas) == 0:
            respostas.append(EM_BRANCO)
        elif len(marcadas) > 1:
            respostas.append(MAIS_DE_UMA_MARCADA)
        else:
            respostas.append(OPCOES[marcadas[0]])
    return respostas
