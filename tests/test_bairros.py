from src.bairros import (ALIAS, APROXIMADO, EXATO, NAO_BAIRRO, NAO_ENCONTRADO, NULO,
                         normalize_name, resolve_bairro)

OFICIAIS = ["BOA VIAGEM", "GRACAS", "IMBIRIBEIRA", "RECIFE", "SAO JOSE", "VASCO DA GAMA"]


def test_normaliza_acento_caixa_e_espacos():
    assert normalize_name("  São   José ") == "SAO JOSE"
    assert normalize_name("Boa-Viagem") == "BOA VIAGEM"
    assert normalize_name(None) is None
    assert normalize_name("   ") is None


def test_igualdade_exata_apos_normalizar():
    assert resolve_bairro("Graças", OFICIAIS) == ("GRACAS", EXATO)


def test_recife_e_bairro_valido():
    assert resolve_bairro("RECIFE", OFICIAIS) == ("RECIFE", EXATO)


def test_apelido_para_erro_conhecido():
    assert resolve_bairro("GRAAS", OFICIAIS) == ("GRACAS", ALIAS)
    assert resolve_bairro("INBIRIBEIRA", OFICIAIS) == ("IMBIRIBEIRA", ALIAS)
    assert resolve_bairro("VASIO  DAGAMA", OFICIAIS) == ("VASCO DA GAMA", ALIAS)


def test_correspondencia_aproximada_com_limiar_alto():
    assert resolve_bairro("BOA VIAGEMM", OFICIAIS) == ("BOA VIAGEM", APROXIMADO)


def test_nao_bairro_nulo_e_desconhecido():
    assert resolve_bairro("ZONA RURAL", OFICIAIS) == (None, NAO_BAIRRO)
    assert resolve_bairro("centro", OFICIAIS) == (None, NAO_BAIRRO)
    assert resolve_bairro(None, OFICIAIS) == (None, NULO)
    assert resolve_bairro("PACHECO", OFICIAIS) == (None, NAO_ENCONTRADO)
