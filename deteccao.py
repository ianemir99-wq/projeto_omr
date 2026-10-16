import cv2

from configuracoes import (AREA_MINIMA_RELATIVA, AREA_MAXIMA_RELATIVA, PROPORCAO_MINIMA,
                           PROPORCAO_MAXIMA, TOLERANCIA_AREA_MINIMA, TOLERANCIA_AREA_MAXIMA,
                           TOTAL_DE_BOLINHAS, QUANTIDADE_DE_COLUNAS, BOLINHAS_POR_COLUNA,
                           QUESTOES_POR_COLUNA, OPCOES)


def achar_bolinhas(imagem_binaria):
    # tem que ser RETR_CCOMP porque as bolinhas ficam dentro das caixinhas da tabela
    # (com RETR_EXTERNAL so achava 20 das 120)
    contornos, hierarquia = cv2.findContours(imagem_binaria, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    area_da_imagem = imagem_binaria.shape[0] * imagem_binaria.shape[1]
    area_minima = area_da_imagem * AREA_MINIMA_RELATIVA
    area_maxima = area_da_imagem * AREA_MAXIMA_RELATIVA

    # pega tudo que tem tamanho e formato de bolinha
    candidatos = []
    for indice in range(len(contornos)):
        # o CCOMP tambem devolve o buraco de dentro de cada bolinha, esses eu pulo
        if hierarquia[0][indice][3] != -1:
            continue
        x, y, largura, altura = cv2.boundingRect(contornos[indice])
        area = cv2.contourArea(contornos[indice])
        proporcao = largura / altura
        if area_minima < area < area_maxima and PROPORCAO_MINIMA < proporcao < PROPORCAO_MAXIMA:
            candidatos.append((x, y, largura, altura, area))

    # as letras de dentro das bolinhas tambem viram contorno,
    # entao tiro tudo que estiver dentro de outro candidato
    candidatos_sem_letras = []
    for candidato in candidatos:
        if not esta_dentro_de_outro(candidato, candidatos):
            candidatos_sem_letras.append(candidato)
    candidatos = candidatos_sem_letras

    # todas as bolinhas tem quase o mesmo tamanho, entao tiro o que for muito diferente
    if len(candidatos) > 0:
        area_normal = pegar_mediana([candidato[4] for candidato in candidatos])
        candidatos_com_tamanho_certo = []
        for candidato in candidatos:
            if TOLERANCIA_AREA_MINIMA * area_normal <= candidato[4] <= TOLERANCIA_AREA_MAXIMA * area_normal:
                candidatos_com_tamanho_certo.append(candidato)
        candidatos = candidatos_com_tamanho_certo

    # se ainda sobrou mais que 120, fico com as de area mais parecida com a normal
    if len(candidatos) > TOTAL_DE_BOLINHAS:
        area_normal = pegar_mediana([candidato[4] for candidato in candidatos])
        candidatos = sorted(candidatos, key=lambda candidato: abs(candidato[4] - area_normal))
        candidatos = candidatos[:TOTAL_DE_BOLINHAS]

    bolinhas = []
    for x, y, largura, altura, area in candidatos:
        bolinhas.append((x, y, largura, altura))

    # quando a marcacao encosta na linha da tabela a bolinha vira parte da tabela e some
    # se sumiu no maximo uma por coluna da pra recriar
    if TOTAL_DE_BOLINHAS - QUANTIDADE_DE_COLUNAS <= len(bolinhas) < TOTAL_DE_BOLINHAS:
        bolinhas = recuperar_bolinhas_faltando(bolinhas)

    return bolinhas


def pegar_mediana(valores):
    valores = sorted(valores)
    return valores[len(valores) // 2]


def esta_dentro_de_outro(candidato, candidatos):
    x, y, largura, altura = candidato[:4]
    centro_x = x + largura / 2
    centro_y = y + altura / 2
    for outro in candidatos:
        outro_x, outro_y, outra_largura, outra_altura = outro[:4]
        outro_e_maior = outra_largura * outra_altura > largura * altura
        centro_dentro_do_outro = (outro_x < centro_x < outro_x + outra_largura
                                  and outro_y < centro_y < outro_y + outra_altura)
        if outro_e_maior and centro_dentro_do_outro:
            return True
    return False


def recuperar_bolinhas_faltando(bolinhas):
    """Recria no maximo uma bolinha faltando em cada coluna do gabarito."""
    bolinhas_por_x = sorted(bolinhas, key=lambda bolinha: bolinha[0])

    # o espaco entre as colunas e bem maior que entre as opcoes,
    # entao os 2 maiores pulos no x mostram onde cada coluna termina
    pulos = []
    for indice in range(len(bolinhas_por_x) - 1):
        distancia = bolinhas_por_x[indice + 1][0] - bolinhas_por_x[indice][0]
        pulos.append((distancia, indice))
    pulos.sort(reverse=True)

    onde_cortar = []
    for distancia, indice in pulos[:QUANTIDADE_DE_COLUNAS - 1]:
        onde_cortar.append(indice)
    onde_cortar.sort()

    colunas = []
    inicio = 0
    for indice in onde_cortar:
        colunas.append(bolinhas_por_x[inicio:indice + 1])
        inicio = indice + 1
    colunas.append(bolinhas_por_x[inicio:])

    for numero_da_coluna in range(len(colunas)):
        if len(colunas[numero_da_coluna]) == BOLINHAS_POR_COLUNA - 1:
            colunas[numero_da_coluna] = recriar_bolinha_da_coluna(colunas[numero_da_coluna])

    todas_as_bolinhas = []
    for coluna in colunas:
        todas_as_bolinhas += coluna
    return todas_as_bolinhas


def recriar_bolinha_da_coluna(coluna):
    coluna = sorted(coluna, key=lambda bolinha: bolinha[1])
    altura_normal = pegar_mediana([bolinha[3] for bolinha in coluna])

    # separa em linhas: quando o y da um pulo grande comeca uma linha nova
    linhas = [[coluna[0]]]
    for bolinha in coluna[1:]:
        ultima_bolinha = linhas[-1][-1]
        if bolinha[1] - ultima_bolinha[1] > altura_normal * 0.7:
            linhas.append([bolinha])
        else:
            linhas[-1].append(bolinha)

    quantidade_de_opcoes = len(OPCOES)
    linhas_completas = []
    linhas_incompletas = []
    for linha in linhas:
        if len(linha) == quantidade_de_opcoes:
            linhas_completas.append(sorted(linha, key=lambda bolinha: bolinha[0]))
        elif len(linha) == quantidade_de_opcoes - 1:
            linhas_incompletas.append(linha)

    # tem que ter 9 linhas certinhas e 1 faltando uma bolinha, senao nao mexo em nada
    if len(linhas_completas) != QUESTOES_POR_COLUNA - 1 or len(linhas_incompletas) != 1:
        return coluna

    # x de cada opcao (A, B, C, D) olhando as linhas completas
    x_das_opcoes = []
    for indice_opcao in range(quantidade_de_opcoes):
        x_das_opcoes.append(pegar_mediana([linha[indice_opcao][0] for linha in linhas_completas]))

    # descobre qual opcao esta faltando na linha incompleta
    linha_incompleta = sorted(linhas_incompletas[0], key=lambda bolinha: bolinha[0])
    opcoes_encontradas = []
    desvios = []
    for bolinha in linha_incompleta:
        x = bolinha[0]
        opcao_mais_perto = 0
        for indice_opcao in range(quantidade_de_opcoes):
            if abs(x - x_das_opcoes[indice_opcao]) < abs(x - x_das_opcoes[opcao_mais_perto]):
                opcao_mais_perto = indice_opcao
        opcoes_encontradas.append(opcao_mais_perto)
        desvios.append(x - x_das_opcoes[opcao_mais_perto])

    opcoes_faltando = []
    for indice_opcao in range(quantidade_de_opcoes):
        if indice_opcao not in opcoes_encontradas:
            opcoes_faltando.append(indice_opcao)
    if len(opcoes_faltando) != 1:
        return coluna

    # a bolinha nova fica no x da opcao (corrigido pelo desvio da linha) e no y da linha
    novo_x = x_das_opcoes[opcoes_faltando[0]] + sum(desvios) / len(desvios)
    novo_y = sum(bolinha[1] for bolinha in linha_incompleta) / len(linha_incompleta)
    largura = linha_incompleta[0][2]
    altura = linha_incompleta[0][3]
    coluna.append((int(novo_x), int(novo_y), largura, altura))
    return coluna
