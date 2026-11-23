"""Apelidos manuais para nomes de bairro digitados errado nos CSVs do portal.

As chaves já estão normalizadas (maiúsculas, sem acento, só A-Z, 0-9 e espaço);
os valores são nomes da Tabela de Bairros do portal, também normalizados.
Foram levantadas olhando os nomes que não batiam com a tabela em 2015-2025.
"""

ALIASES = {
    # acento/caractere perdido na origem
    "GRAAS": "GRACAS",
    "TAMA": "TAMARINEIRA",
    "MORRO DA CONCEIO": "MORRO DA CONCEICAO",
    "MORRO DA CONCEIAO": "MORRO DA CONCEICAO",
    "SO JOSE": "SAO JOSE",
    "JORDO": "JORDAO",
    "FUNDO": "FUNDAO",  # "FUNDÃO" com caractere corrompido
    "BOMBA DO HEMETRIO": "BOMBA DO HEMETERIO",
    "ALTO JOS DO PINHO": "ALTO JOSE DO PINHO",
    "CHO DE ESTRELA": "CHAO DE ESTRELA",
    # erros de digitação
    "INBIRIBEIRA": "IMBIRIBEIRA",
    "VASIO DAGAMA": "VASCO DA GAMA",
    "MUSTADINHA": "MUSTARDINHA",
    "PONRO DE PARADA": "PONTO DE PARADA",
    "MANGABERIA": "MANGABEIRA",
    "TEJIPI": "TEJIPIO",
    "SAN MARTIM": "SAN MARTIN",
    "CORDRIRO": "CORDEIRO",
    "SANTE AMARO": "SANTO AMARO",
    "SANATO AMARO": "SANTO AMARO",
    "AREAIS": "AREIAS",
    "MACAEIRA": "MACAXEIRA",  # "MACA\EIRA" com caractere corrompido
    "JIQU": "JIQUIA",
    # variações de nome
    "JOANA BEZERRA": "ILHA JOANA BEZERRA",
    "MANGUEIRA BAIRRO": "MANGUEIRA",
    "JD JORDAO": "JORDAO",
    "CORREGO JENIPAPO": "CORREGO DO JENIPAPO",
    "BREJO DE GUABIRABA": "BREJO DA GUABIRABA",
    "VASCO": "VASCO DA GAMA",
    "VASC": "VASCO DA GAMA",
}

# Valores que aparecem no campo de bairro mas não são um bairro do Recife
NOT_BAIRRO = {"ZONA RURAL", "CENTRO", "BAIRRO IGNORADO"}
