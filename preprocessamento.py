import cv2

from configuracoes import TAMANHO_DO_BLUR, TAMANHO_DO_BLOCO, CONSTANTE_DO_THRESHOLD


def carregar_imagem(caminho_da_imagem):
    imagem = cv2.imread(str(caminho_da_imagem))
    # o imread nao da erro se nao achar o arquivo, so devolve None
    if imagem is None:
        raise FileNotFoundError(f"Não consegui abrir a imagem: {caminho_da_imagem}")
    return imagem


def preprocessar_imagem(imagem):
    imagem_cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    imagem_borrada = cv2.GaussianBlur(imagem_cinza, (TAMANHO_DO_BLUR, TAMANHO_DO_BLUR), 0)

    # threshold adaptativo pra aguentar as sombras das fotos
    # o INV deixa as marcas brancas e o fundo preto
    imagem_binaria = cv2.adaptiveThreshold(imagem_borrada, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, TAMANHO_DO_BLOCO,
                                           CONSTANTE_DO_THRESHOLD)
    return imagem_binaria
