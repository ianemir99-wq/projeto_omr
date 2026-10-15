"""
testar.py - Avalia o leitor de gabaritos (pacote omr) em todo o dataset.

Uso:
    python testar.py               # relatório de acurácia
    python testar.py --mostrar 5   # além disso, abre as 5 piores imagens
"""

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

import omr

BASE = Path(__file__).parent
PASTA_IMAGENS = BASE / "omr_dataset" / "OMR_Image_Resized"
ARQUIVO_CSV = BASE / "omr_dataset" / "OMR_Ans.csv"

# O CSV usa palavras para questão em branco / múltipla marcação.
# Traduzimos para os mesmos símbolos que o pacote omr devolve.
TRADUCAO = {"BLANK": omr.EM_BRANCO, "MULTI": omr.MULTIPLA}


def normalizar(valor):
    """Valor do CSV -> 'A'..'D', '-' ou '*'."""
    if pd.isna(valor):
        return omr.EM_BRANCO
    texto = str(valor).strip().upper()
    return TRADUCAO.get(texto, texto)


def classificar_erro(lida, esperada):
    """Dá um nome ao tipo de erro (para entender onde o programa falha)."""
    if lida == omr.EM_BRANCO:
        return "Leu em BRANCO, mas havia marcação"
    if lida == omr.MULTIPLA:
        return "Leu DUPLA, mas não era"
    if esperada == omr.EM_BRANCO:
        return "Leu uma letra, mas o gabarito diz BRANCO"
    if esperada == omr.MULTIPLA:
        return "Leu uma letra, mas o gabarito diz DUPLA"
    return "Trocou de letra (A/B/C/D)"


def main():
    parser = argparse.ArgumentParser(description="Avalia o leitor OMR no dataset.")
    parser.add_argument("--mostrar", type=int, default=0, metavar="N",
                        help="abre as N piores imagens (verde=acertou, "
                             "vermelho=errou, amarelo=resposta do CSV)")
    args = parser.parse_args()

    df = pd.read_csv(ARQUIVO_CSV).dropna(subset=["Image_ID"])

    total_acertos = 0
    total_questoes = 0
    erros = Counter()
    resultados = []        # (acertos, id_imagem)
    leituras = {}          # id_imagem -> (respostas, questoes), para as janelas
    falhas = []

    print(f"Avaliando {len(df)} imagens...")
    for _, linha in df.iterrows():
        id_imagem = int(linha["Image_ID"])
        esperado = [normalizar(v) for v in linha.iloc[1:]]
        total_questoes += len(esperado)

        try:
            imagem = omr.carregar_imagem(PASTA_IMAGENS / f"{id_imagem}.jpg")
            respostas, questoes = omr.ler_gabarito(imagem)
        except (FileNotFoundError, omr.GabaritoNaoDetectado):
            falhas.append(id_imagem)       # conta como 0 acertos
            resultados.append((0, id_imagem))
            continue

        leituras[id_imagem] = (respostas, questoes)
        acertos = 0
        for lida, certa in zip(respostas, esperado):
            if lida == certa:
                acertos += 1
            else:
                erros[classificar_erro(lida, certa)] += 1

        total_acertos += acertos
        resultados.append((acertos, id_imagem))

    # ----- Relatório -----
    perfeitas = sum(1 for acertos, _ in resultados if acertos == omr.TOTAL_QUESTOES)
    print("=" * 50)
    print(f"Imagens avaliadas:         {len(resultados)}")
    print(f"Imagens com falha:         {len(falhas)}")
    print(f"Imagens 100% corretas:     {perfeitas}")
    print(f"Questões corretas:         {total_acertos} de {total_questoes}")
    print(f"ACURÁCIA:                  {100 * total_acertos / total_questoes:.1f}%")
    print("=" * 50)

    if erros:
        print("\nTipos de erro:")
        for tipo, quantidade in erros.most_common():
            print(f"  {quantidade:4d}  {tipo}")

    piores = sorted(resultados)[:10]
    print("\nAs 10 piores imagens:")
    for acertos, id_imagem in piores:
        print(f"  {id_imagem}.jpg -> {acertos}/{omr.TOTAL_QUESTOES}")
    if falhas:
        print("\nImagens em que a detecção falhou:", falhas)

    # ----- Janelas com as piores imagens -----
    for acertos, id_imagem in piores[: args.mostrar]:
        if id_imagem not in leituras:
            continue
        respostas, questoes = leituras[id_imagem]
        linha = df[df["Image_ID"] == id_imagem].iloc[0, 1:]
        esperado = [normalizar(v) for v in linha]

        imagem = omr.carregar_imagem(PASTA_IMAGENS / f"{id_imagem}.jpg")
        desenho = omr.desenhar_respostas(imagem, questoes, respostas, esperado)
        titulo = f"Imagem {id_imagem}: {acertos}/{omr.TOTAL_QUESTOES} (ESC para sair)"
        if omr.mostrar_janela(titulo, desenho) == 27:
            break


if __name__ == "__main__":
    main()