# configuracoes do leitor de gabarito
# os valores foram ajustados testando nas fotos do dataset

# formato do gabarito: 3 colunas de 10 questoes, cada uma com as opcoes A, B, C e D
QUANTIDADE_DE_COLUNAS = 3
QUESTOES_POR_COLUNA = 10
OPCOES = "ABCD"

BOLINHAS_POR_COLUNA = QUESTOES_POR_COLUNA * len(OPCOES)          # 40
TOTAL_DE_BOLINHAS = QUANTIDADE_DE_COLUNAS * BOLINHAS_POR_COLUNA   # 120
TOTAL_DE_QUESTOES = QUANTIDADE_DE_COLUNAS * QUESTOES_POR_COLUNA   # 30

# o que aparece na resposta quando nao tem uma letra so
EM_BRANCO = "-"
MAIS_DE_UMA_MARCADA = "*"

# preprocessamento (blur + threshold adaptativo)
TAMANHO_DO_BLUR = 5
TAMANHO_DO_BLOCO = 31          # tem que ser impar
CONSTANTE_DO_THRESHOLD = 10

# filtros pra achar as bolinhas
# a area e uma fracao da area da imagem, assim funciona com foto de qualquer tamanho
AREA_MINIMA_RELATIVA = 0.0002
AREA_MAXIMA_RELATIVA = 0.008
PROPORCAO_MINIMA = 0.6         # largura / altura
PROPORCAO_MAXIMA = 1.6
TOLERANCIA_AREA_MINIMA = 0.5   # aceita de 50% ate 200% da area de uma bolinha normal
TOLERANCIA_AREA_MAXIMA = 2.0

# leitura
LIMITE_PREENCHIMENTO = 0.5     # de 0.4 a 0.6 o resultado foi quase igual, fiquei com 0.5
MARGEM_DO_RAIO = 3             # diminui o circulo pra nao contar a borda impressa da bolinha
