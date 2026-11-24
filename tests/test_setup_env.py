import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, ROOT / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


setup_env = carregar("setup_env")
doctor = carregar("doctor")
EXEMPLO = (ROOT / ".env.example").read_text(encoding="utf-8")


def test_gera_segredos_no_lugar_do_texto_de_exemplo():
    texto, geradas = setup_env.build_env(EXEMPLO)
    valores = setup_env.parse_env(texto)
    assert set(geradas) == set(setup_env.GERADORES)
    for chave in setup_env.GERADORES:
        assert not setup_env.e_exemplo(valores[chave])
    assert re.fullmatch(r"[A-Za-z0-9]{24}", valores["POSTGRES_PASSWORD"])
    assert len(valores["DASHBOARD_PASSWORD"]) >= 16
    assert valores["DASHBOARD_USER"] == "g15" and valores["BIND_ADDRESS"] == "127.0.0.1"
    assert valores["DASHBOARD_AUTH"] == "on"


def test_nao_troca_valores_existentes_e_e_idempotente():
    primeiro, _ = setup_env.build_env(EXEMPLO)
    segundo, geradas = setup_env.build_env(EXEMPLO, primeiro)
    assert geradas == [] and setup_env.parse_env(segundo) == setup_env.parse_env(primeiro)


def test_gera_so_o_que_falta_e_preserva_chaves_extras():
    atual = "POSTGRES_PASSWORD=abc123\nDASHBOARD_PASSWORD=troque-a-senha-do-painel\nMINHA_CHAVE=1\n"
    texto, geradas = setup_env.build_env(EXEMPLO, atual)
    valores = setup_env.parse_env(texto)
    assert valores["POSTGRES_PASSWORD"] == "abc123" and valores["MINHA_CHAVE"] == "1"
    assert "POSTGRES_PASSWORD" not in geradas and "DASHBOARD_PASSWORD" in geradas
    assert not setup_env.e_exemplo(valores["DASHBOARD_PASSWORD"])


def test_ajustes_forcam_valores_e_main_nao_imprime_segredos(tmp_path, capsys):
    destino = tmp_path / ".env"
    assert setup_env.main(["--env", str(destino), "--set", "API_HOST_PORT=18000"]) == 0
    valores = setup_env.parse_env(destino.read_text(encoding="utf-8"))
    saida = capsys.readouterr().out
    assert valores["API_HOST_PORT"] == "18000"
    for chave in setup_env.GERADORES:
        assert valores[chave] not in saida
    assert "DASHBOARD_PASSWORD" in saida


def test_doctor_detecta_segredos_de_exemplo_e_rede_aberta():
    achados = doctor.check_env({"POSTGRES_PASSWORD": "troque-esta-senha", "BIND_ADDRESS": "0.0.0.0"})
    textos = [t for _, t in achados]
    assert any(n == "ERRO" and "POSTGRES_PASSWORD" in t for n, t in achados)
    assert any("BIND_ADDRESS=0.0.0.0" in t for t in textos)
    assert any("Mosquitto anônimo" in t for t in textos)


def test_doctor_aceita_env_gerado_e_ignora_senha_do_painel_com_auth_off():
    texto, _ = setup_env.build_env(EXEMPLO)
    assert not [n for n, _ in doctor.check_env(setup_env.parse_env(texto)) if n == "ERRO"]
    valores = setup_env.parse_env(texto) | {"DASHBOARD_AUTH": "off", "DASHBOARD_PASSWORD": ""}
    achados = doctor.check_env(valores)
    assert not [n for n, _ in achados if n == "ERRO"] and any("DASHBOARD_AUTH=off" in t for _, t in achados)


def test_demo_nao_imprime_a_senha():
    for nome in ("demo.sh", "demo.ps1"):
        texto = (ROOT / "scripts" / nome).read_text(encoding="utf-8-sig")
        assert "DASHBOARD_PASSWORD no arquivo .env" in texto and "DASHBOARD_AUTH=off" in texto
