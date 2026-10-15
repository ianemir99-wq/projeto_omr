"""
omr.py - Leitor de gabaritos de múltipla escolha (OMR) com OpenCV puro.

Recebe a foto de um gabarito com 30 questões (3 colunas de 10, opções A-D)
e devolve a resposta marcada em cada questão.

Pipeline:
    foto -> pré-processamento -> detecção das bolinhas -> organização
         -> medição do preenchimento -> respostas

Uso como biblioteca:
    import omr
    imagem = omr.carregar_imagem("foto.jpg")
    respostas, questoes = omr.ler_gabarito(imagem)
    print(respostas)        # ['C', 'C', 'D', ..., '-', '*']

Uso pela linha de comando:
    python omr.py foto.jpg
"""

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Layout do gabarito
# ---------------------------------------------------------------------------
COLUNAS = 3
LINHAS_POR_COLUNA = 10
OPCOES = "ABCD"
BOLINHAS_POR_COLUNA = LINHAS_POR_COLUNA * len(OPCOES)   # 40
TOTAL_BOLINHAS = COLUNAS * BOLINHAS_POR_COLUNA          # 120
TOTAL_QUESTOES = COLUNAS * LINHAS_POR_COLUNA            # 30

# Símbolos usados no resultado quando não há uma letra única
EM_BRANCO = "-"   # nenhuma opção marcada
MULTIPLA = "*"    # mais de uma opção marcada

# ---------------------------------------------------------------------------
# Parâmetros (ajustados olhando o dataset)
# ---------------------------------------------------------------------------
# Pré-processamento
TAMANHO_BLUR = 5             # tamanho do blur gaussiano (ímpar)
TAMANHO_BLOCO = 31          # vizinhança do threshold adaptativo (ímpar)
CONSTANTE_THRESHOLD = 10    # subtraída da média local no threshold

# Detecção das bolinhas: limites de área RELATIVOS ao tamanho da imagem,
# para funcionar em qualquer resolução.
AREA_MIN_REL = 0.0002
AREA_MAX_REL = 0.008
PROPORCAO_MIN = 0.6         # largura / altura mínima
PROPORCAO_MAX = 1.6         # largura / altura máxima
TOLERANCIA_AREA_MIN = 0.5   # aceita áreas a partir de 50% da área típica da bolinha
TOLERANCIA_AREA_MAX = 2.0   # ... até 200% dela

# Leitura: fração mínima da bolinha que precisa estar escura para contar como marcada
LIMITE_PREENCHIMENTO = 0.5
MARGEM_RAIO = 3             # encolhe o círculo medido para ignorar a borda impressa


class GabaritoNaoDetectado(Exception):
    """A foto não tem as 120 bolinhas esperadas (foto ruim, cortada ou outro modelo)."""


# ---------------------------------------------------------------------------
# 1. Carregar e pré-processar
# ---------------------------------------------------------------------------
def carregar_imagem(caminho):
    """Abre uma imagem. O cv2.imread devolve None em silêncio se falhar,
    então transformamos isso em um erro claro."""
    imagem = cv2.imread(str(caminho))
    if imagem is None:
        raise FileNotFoundError(f"Não consegui abrir a imagem: {caminho}")
    return imagem


def preprocessar(imagem):
    """Imagem colorida -> imagem binária (marcas e contornos em BRANCO, fundo preto).

    O threshold é adaptativo (compara cada pixel com a média da vizinhança),
    por isso aguenta sombra e iluminação desigual."""
    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    borrada = cv2.GaussianBlur(cinza, (TAMANHO_BLUR, TAMANHO_BLUR), 0)
    return cv2.adaptiveThreshold(
        borrada, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
        TAMANHO_BLOCO, CONSTANTE_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# 2. Detectar as bolinhas
# ---------------------------------------------------------------------------
def achar_bolinhas(binaria):
    """Devolve a lista de bolinhas como retângulos (x, y, w, h).

    Detalhes importantes:
    - Usa RETR_CCOMP porque as bolinhas ficam dentro das "caixinhas" da tabela;
      com RETR_EXTERNAL elas seriam ignoradas.
    - O CCOMP também devolve o "buraco" de cada anel, que descartamos pela hierarquia.
    - Formas de tamanho muito diferente do típico (dígitos, letras) são descartadas.
    - Se faltar exatamente uma (ex.: rabisco colado), ela é recriada pela geometria."""
    contornos, hierarquia = cv2.findContours(
        binaria, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )[-2:]

    area_imagem = binaria.shape[0] * binaria.shape[1]
    area_min = area_imagem * AREA_MIN_REL
    area_max = area_imagem * AREA_MAX_REL

    # 1) Candidatos: tamanho e formato de bolinha
    candidatos = []
    for i, contorno in enumerate(contornos):
        if hierarquia[0][i][3] != -1:      # é buraco de anel, não bolinha
            continue
        x, y, w, h = cv2.boundingRect(contorno)
        area = cv2.contourArea(contorno)
        if area_min < area < area_max and PROPORCAO_MIN < w / h < PROPORCAO_MAX:
            candidatos.append((x, y, w, h, area))

    # 2) Letras dentro dos anéis também viram contornos. Uma bolinha nunca fica
    #    dentro de outra, então descartamos quem está dentro de outro candidato.
    candidatos = [c for c in candidatos if not _esta_dentro_de_outro(c, candidatos)]

    # 3) Todas as bolinhas têm tamanho parecido: descarta o que destoa da mediana
    if candidatos:
        mediana = _mediana_das_areas(candidatos)
        candidatos = [c for c in candidatos
                      if TOLERANCIA_AREA_MIN * mediana <= c[4] <= TOLERANCIA_AREA_MAX * mediana]

    # 4) Se ainda sobrar forma a mais, ficam as de tamanho mais próximo do típico
    if len(candidatos) > TOTAL_BOLINHAS:
        mediana = _mediana_das_areas(candidatos)
        candidatos = sorted(candidatos, key=lambda c: abs(c[4] - mediana))[:TOTAL_BOLINHAS]

    bolinhas = [(x, y, w, h) for (x, y, w, h, _) in candidatos]

    # 5) Se faltou exatamente uma, recria pela geometria das outras
    if len(bolinhas) == TOTAL_BOLINHAS - 1:
        bolinhas = _completar_faltante(bolinhas)

    return bolinhas


def _mediana_das_areas(candidatos):
    areas = sorted(c[4] for c in candidatos)
    return areas[len(areas) // 2]


def _esta_dentro_de_outro(candidato, candidatos):
    """True se o centro deste candidato cai dentro do retângulo de um candidato maior."""
    x, y, w, h = candidato[:4]
    cx, cy = x + w / 2, y + h / 2
    for outro in candidatos:
        ox, oy, ow, oh = outro[:4]
        if ow * oh > w * h and ox < cx < ox + ow and oy < cy < oy + oh:
            return True
    return False


def _completar_coluna(coluna):
    """Recebe uma coluna com 39 bolinhas e recria a que falta."""
    coluna = sorted(coluna, key=lambda b: b[1])              # de cima para baixo
    altura = sorted(b[3] for b in coluna)[len(coluna) // 2]  # altura típica

    # Agrupa em linhas: começa linha nova quando o y dá um salto grande
    linhas = [[coluna[0]]]
    for b in coluna[1:]:
        if b[1] - linhas[-1][-1][1] > altura * 0.7:
            linhas.append([b])
        else:
            linhas[-1].append(b)

    n = len(OPCOES)
    completas = [sorted(l, key=lambda b: b[0]) for l in linhas if len(l) == n]
    incompletas = [l for l in linhas if len(l) == n - 1]

    if len(completas) != LINHAS_POR_COLUNA - 1 or len(incompletas) != 1:
        return coluna   # situação estranha: não mexe

    # Posição x típica (mediana) de cada opção nas linhas completas
    tipicos = []
    for i in range(n):
        xs = sorted(l[i][0] for l in completas)
        tipicos.append(xs[len(xs) // 2])

    # Descobre qual opção falta na linha incompleta
    linha = sorted(incompletas[0], key=lambda b: b[0])
    usados, desvios = [], []
    for (x, y, w, h) in linha:
        i = min(range(n), key=lambda k: abs(x - tipicos[k]))
        usados.append(i)
        desvios.append(x - tipicos[i])

    faltou = [i for i in range(n) if i not in usados]
    if len(faltou) != 1:
        return coluna

    # Cria a bolinha: x típico da opção (ajustado pelo desvio da linha) e y da linha
    novo_x = tipicos[faltou[0]] + sum(desvios) / len(desvios)
    novo_y = sum(b[1] for b in linha) / len(linha)
    coluna.append((int(novo_x), int(novo_y), linha[0][2], linha[0][3]))
    return coluna


def _completar_faltante(bolinhas):
    """Se faltar exatamente UMA bolinha, cria ela na posição onde deveria estar."""
    por_x = sorted(bolinhas, key=lambda b: b[0])

    # As maiores lacunas horizontais separam as colunas
    lacunas = sorted(
        ((por_x[i + 1][0] - por_x[i][0], i) for i in range(len(por_x) - 1)),
        reverse=True,
    )
    cortes = sorted(i for _, i in lacunas[: COLUNAS - 1])
    limites = [-1] + cortes + [len(por_x) - 1]
    colunas = [por_x[limites[k] + 1 : limites[k + 1] + 1] for k in range(COLUNAS)]

    for k, coluna in enumerate(colunas):
        if len(coluna) == BOLINHAS_POR_COLUNA - 1:
            colunas[k] = _completar_coluna(coluna)

    return [b for coluna in colunas for b in coluna]


# ---------------------------------------------------------------------------
# 3. Organizar em questões
# ---------------------------------------------------------------------------
def organizar(bolinhas):
    """Converte as 120 bolinhas desordenadas em 30 questões.

    Devolve uma lista de 30 itens; cada item tem 4 bolinhas na ordem A, B, C, D.
    questoes[0] é a questão 1, questoes[10] é a questão 11, e assim por diante."""
    if len(bolinhas) != TOTAL_BOLINHAS:
        raise GabaritoNaoDetectado(
            f"Encontrei {len(bolinhas)} bolinhas, esperava {TOTAL_BOLINHAS}."
        )

    n = len(OPCOES)
    bolinhas = sorted(bolinhas, key=lambda b: b[0])   # esquerda -> direita

    questoes = []
    for col in range(COLUNAS):
        # 1) Fatia de 40 bolinhas = uma coluna do gabarito
        coluna = bolinhas[col * BOLINHAS_POR_COLUNA : (col + 1) * BOLINHAS_POR_COLUNA]
        coluna = sorted(coluna, key=lambda b: b[1])   # 2) cima -> baixo
        for linha in range(LINHAS_POR_COLUNA):
            opcoes = coluna[linha * n : (linha + 1) * n]          # 3) grupos de 4
            questoes.append(sorted(opcoes, key=lambda b: b[0]))   # 4) A, B, C, D
    return questoes


# ---------------------------------------------------------------------------
# 4. Ler as respostas
# ---------------------------------------------------------------------------
def preenchimento(binaria, bolinha):
    """Quanto da bolinha está preenchida, de 0.0 (vazia) a 1.0 (cheia).

    Mede só o miolo do círculo (ignora o contorno impresso): conta os pixels
    brancos da imagem binária dentro de uma máscara circular."""
    x, y, w, h = bolinha
    raio = max(min(w, h) // 2 - MARGEM_RAIO, 1)

    x0, y0 = max(x, 0), max(y, 0)
    recorte = binaria[y0 : y + h, x0 : x + w]
    mascara = np.zeros_like(recorte)
    cv2.circle(mascara, (x + w // 2 - x0, y + h // 2 - y0), raio, 255, -1)

    area_circulo = cv2.countNonZero(mascara)
    if area_circulo == 0:
        return 0.0
    brancos = cv2.countNonZero(cv2.bitwise_and(recorte, recorte, mask=mascara))
    return brancos / area_circulo


def ler_respostas(binaria, questoes, limite=LIMITE_PREENCHIMENTO):
    """Devolve a resposta de cada questão:
    'A'..'D' = marcada | '-' = em branco | '*' = mais de uma marcada."""
    respostas = []
    for opcoes in questoes:
        valores = [preenchimento(binaria, b) for b in opcoes]
        marcadas = [i for i, v in enumerate(valores) if v >= limite]

        if len(marcadas) == 0:
            respostas.append(EM_BRANCO)
        elif len(marcadas) > 1:
            respostas.append(MULTIPLA)
        else:
            respostas.append(OPCOES[marcadas[0]])
    return respostas


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------
def ler_gabarito(imagem, limite=LIMITE_PREENCHIMENTO):
    """Pipeline completo: imagem colorida (BGR) -> (respostas, questoes).

    Levanta GabaritoNaoDetectado se não achar as 120 bolinhas."""
    binaria = preprocessar(imagem)
    bolinhas = achar_bolinhas(binaria)
    questoes = organizar(bolinhas)
    respostas = ler_respostas(binaria, questoes, limite)
    return respostas, questoes


# ---------------------------------------------------------------------------
# Visualização
# ---------------------------------------------------------------------------
def desenhar_respostas(imagem, questoes, respostas, esperado=None):
    """Devolve uma cópia da imagem com o resultado desenhado.

    Sem `esperado`:  verde = resposta lida | vermelho = em branco ou dupla.
    Com `esperado`:  verde = acertou | vermelho = leu errado | amarelo = a certa."""
    VERDE, VERMELHO, AMARELO = (0, 255, 0), (0, 0, 255), (0, 255, 255)

    def caixa(bolinha, cor, espessura):
        x, y, w, h = bolinha
        cv2.rectangle(resultado, (x, y), (x + w, y + h), cor, espessura)

    resultado = imagem.copy()
    for i, (opcoes, lida) in enumerate(zip(questoes, respostas)):
        if esperado is None or lida == esperado[i]:
            if lida in OPCOES:
                caixa(opcoes[OPCOES.index(lida)], VERDE, 3)
            elif esperado is None:
                for b in opcoes:
                    caixa(b, VERMELHO, 1)
        else:
            if lida in OPCOES:
                caixa(opcoes[OPCOES.index(lida)], VERMELHO, 3)
            else:
                for b in opcoes:
                    caixa(b, VERMELHO, 1)
            if esperado[i] in OPCOES:
                caixa(opcoes[OPCOES.index(esperado[i])], AMARELO, 2)
    return resultado


def mostrar_janela(titulo, imagem, altura_max=800):
    """Mostra a imagem inteira (reduz se for maior que a tela) e espera uma tecla.
    Devolve o código da tecla apertada (27 = ESC)."""
    escala = min(1.0, altura_max / imagem.shape[0])
    if escala < 1.0:
        imagem = cv2.resize(imagem, None, fx=escala, fy=escala)
    cv2.imshow(titulo, imagem)
    tecla = cv2.waitKey(0)
    cv2.destroyAllWindows()
    return tecla


# ---------------------------------------------------------------------------
# Linha de comando:  python omr.py foto.jpg
# ---------------------------------------------------------------------------
def _main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Lê um gabarito OMR a partir de uma foto.")
    parser.add_argument("imagem", help="caminho da foto do gabarito")
    parser.add_argument("--sem-janela", action="store_true",
                        help="só imprime as respostas, sem abrir a janela")
    args = parser.parse_args()

    try:
        imagem = carregar_imagem(args.imagem)
        respostas, questoes = ler_gabarito(imagem)
    except (FileNotFoundError, GabaritoNaoDetectado) as erro:
        print(f"Erro: {erro}")
        sys.exit(1)

    print("Respostas lidas  ( - = em branco, * = mais de uma marcada )\n")
    for i in range(LINHAS_POR_COLUNA):
        print("   ".join(
            f"Q{i + 1 + c * LINHAS_POR_COLUNA:>2}: {respostas[i + c * LINHAS_POR_COLUNA]}"
            for c in range(COLUNAS)
        ))

    if not args.sem_janela:
        mostrar_janela("Resultado (verde = resposta lida)",
                       desenhar_respostas(imagem, questoes, respostas))


if __name__ == "__main__":
    _main()