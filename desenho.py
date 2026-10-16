import cv2

from configuracoes import OPCOES

VERDE = (0, 255, 0)
VERMELHO = (0, 0, 255)
AMARELO = (0, 255, 255)


def desenhar_retangulo(imagem, bolinha, cor, espessura):
    x, y, largura, altura = bolinha
    cv2.rectangle(imagem, (x, y), (x + largura, y + altura), cor, espessura)


def desenhar_respostas(imagem, questoes, respostas, respostas_certas=None):
    # sem as respostas certas: verde = resposta lida, vermelho = em branco ou mais de uma
    # com as respostas certas: verde = acertou, vermelho = errou, amarelo = a resposta certa
    resultado = imagem.copy()

    for numero_da_questao in range(len(questoes)):
        opcoes = questoes[numero_da_questao]
        resposta_lida = respostas[numero_da_questao]

        if respostas_certas is None:
            if resposta_lida in OPCOES:
                desenhar_retangulo(resultado, opcoes[OPCOES.index(resposta_lida)], VERDE, 3)
            else:
                for bolinha in opcoes:
                    desenhar_retangulo(resultado, bolinha, VERMELHO, 1)
        else:
            resposta_certa = respostas_certas[numero_da_questao]
            if resposta_lida == resposta_certa:
                if resposta_lida in OPCOES:
                    desenhar_retangulo(resultado, opcoes[OPCOES.index(resposta_lida)], VERDE, 3)
            else:
                if resposta_lida in OPCOES:
                    desenhar_retangulo(resultado, opcoes[OPCOES.index(resposta_lida)], VERMELHO, 3)
                else:
                    for bolinha in opcoes:
                        desenhar_retangulo(resultado, bolinha, VERMELHO, 1)
                if resposta_certa in OPCOES:
                    desenhar_retangulo(resultado, opcoes[OPCOES.index(resposta_certa)], AMARELO, 2)

    return resultado


def mostrar_imagem(titulo, imagem):
    # diminui a imagem se ela for maior que 800 de altura (senao nao cabe na tela)
    escala = min(1.0, 800 / imagem.shape[0])
    if escala < 1.0:
        imagem = cv2.resize(imagem, None, fx=escala, fy=escala)
    cv2.imshow(titulo, imagem)
    tecla = cv2.waitKey(0)
    cv2.destroyAllWindows()
    return tecla   # 27 = ESC
