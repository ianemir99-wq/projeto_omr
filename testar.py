# testa o leitor em todas as fotos do dataset e compara com o gabarito do CSV
#
# uso: python testar.py
#      python testar.py --mostrar 5   (tambem abre as 5 piores imagens)

import sys
from pathlib import Path

import pandas as pd

from configuracoes import EM_BRANCO, MAIS_DE_UMA_MARCADA, TOTAL_DE_QUESTOES
from preprocessamento import carregar_imagem
from desenho import desenhar_respostas, mostrar_imagem
from omr import ler_gabarito, GabaritoNaoDetectado

PASTA_DO_PROJETO = Path(__file__).parent
PASTA_DAS_IMAGENS = PASTA_DO_PROJETO / "omr_dataset" / "OMR_Image_Resized"
ARQUIVO_DO_GABARITO = PASTA_DO_PROJETO / "omr_dataset" / "OMR_Ans.csv"


def converter_resposta_do_csv(valor):
    # no CSV a questao em branco aparece como BLANK e a com mais de uma marcada como MULTI
    if pd.isna(valor):
        return EM_BRANCO
    texto = str(valor).strip().upper()
    if texto == "BLANK":
        return EM_BRANCO
    if texto == "MULTI":
        return MAIS_DE_UMA_MARCADA
    return texto


def descobrir_tipo_do_erro(resposta_lida, resposta_certa):
    if resposta_lida == EM_BRANCO:
        return "Leu em BRANCO, mas havia marcação"
    if resposta_lida == MAIS_DE_UMA_MARCADA:
        return "Leu DUPLA, mas não era"
    if resposta_certa == EM_BRANCO:
        return "Leu uma letra, mas o gabarito diz BRANCO"
    if resposta_certa == MAIS_DE_UMA_MARCADA:
        return "Leu uma letra, mas o gabarito diz DUPLA"
    return "Trocou de letra (A/B/C/D)"


def main():
    quantidade_para_mostrar = 0
    if "--mostrar" in sys.argv:
        posicao = sys.argv.index("--mostrar")
        if posicao + 1 < len(sys.argv):
            quantidade_para_mostrar = int(sys.argv[posicao + 1])

    tabela = pd.read_csv(ARQUIVO_DO_GABARITO)
    tabela = tabela.dropna(subset=["Image_ID"])   # o CSV tem umas linhas vazias no final

    total_de_acertos = 0
    total_de_questoes = 0
    tipos_de_erro = {}
    resultados = []           # (acertos, numero_da_imagem)
    leituras = {}             # guarda o que foi lido pra poder mostrar as imagens no final
    imagens_com_falha = []

    print(f"Avaliando {len(tabela)} imagens...")
    for _, linha in tabela.iterrows():
        numero_da_imagem = int(linha["Image_ID"])
        respostas_certas = [converter_resposta_do_csv(valor) for valor in linha.iloc[1:]]
        total_de_questoes += len(respostas_certas)

        try:
            imagem = carregar_imagem(PASTA_DAS_IMAGENS / f"{numero_da_imagem}.jpg")
            respostas, questoes = ler_gabarito(imagem)
        except (FileNotFoundError, GabaritoNaoDetectado):
            # se nao conseguiu ler a imagem conta como 0 acertos
            imagens_com_falha.append(numero_da_imagem)
            resultados.append((0, numero_da_imagem))
            continue

        leituras[numero_da_imagem] = (respostas, questoes, respostas_certas)
        acertos = 0
        for resposta_lida, resposta_certa in zip(respostas, respostas_certas):
            if resposta_lida == resposta_certa:
                acertos += 1
            else:
                tipo = descobrir_tipo_do_erro(resposta_lida, resposta_certa)
                tipos_de_erro[tipo] = tipos_de_erro.get(tipo, 0) + 1

        total_de_acertos += acertos
        resultados.append((acertos, numero_da_imagem))

    imagens_perfeitas = 0
    for acertos, numero_da_imagem in resultados:
        if acertos == TOTAL_DE_QUESTOES:
            imagens_perfeitas += 1

    print("=" * 50)
    print(f"Imagens avaliadas:         {len(resultados)}")
    print(f"Imagens com falha:         {len(imagens_com_falha)}")
    print(f"Imagens 100% corretas:     {imagens_perfeitas}")
    print(f"Questões corretas:         {total_de_acertos} de {total_de_questoes}")
    print(f"ACURÁCIA:                  {100 * total_de_acertos / total_de_questoes:.1f}%")
    print("=" * 50)

    if len(tipos_de_erro) > 0:
        print("\nTipos de erro:")
        erros_ordenados = sorted(tipos_de_erro.items(), key=lambda item: item[1], reverse=True)
        for tipo, quantidade in erros_ordenados:
            print(f"  {quantidade}  {tipo}")

    piores = sorted(resultados)[:10]
    print("\nAs 10 piores imagens:")
    for acertos, numero_da_imagem in piores:
        print(f"  {numero_da_imagem}.jpg -> {acertos}/{TOTAL_DE_QUESTOES}")
    if len(imagens_com_falha) > 0:
        print("\nImagens em que a detecção falhou:", imagens_com_falha)

    # abre as piores imagens, ESC fecha
    for acertos, numero_da_imagem in piores[:quantidade_para_mostrar]:
        if numero_da_imagem not in leituras:
            continue
        respostas, questoes, respostas_certas = leituras[numero_da_imagem]
        imagem = carregar_imagem(PASTA_DAS_IMAGENS / f"{numero_da_imagem}.jpg")
        desenho = desenhar_respostas(imagem, questoes, respostas, respostas_certas)
        titulo = f"Imagem {numero_da_imagem}: {acertos}/{TOTAL_DE_QUESTOES} (ESC para sair)"
        if mostrar_imagem(titulo, desenho) == 27:
            break


if __name__ == "__main__":
    main()
