"""Confere se o ambiente está pronto para subir a pilha (docker compose) e aponta riscos de configuração.

Uso: python scripts/doctor.py
Saída: OK, AVISO ou ERRO por verificação. Termina com código 1 se houver ERRO. Nunca imprime senhas.
"""
import json
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_env import GERADORES, e_exemplo, parse_env

ARQUIVOS_MINIMOS = [
    "models/best_model.joblib", "models/model_meta.json", "data/processed/panel.csv",
    "data/processed/clima_semanal.csv", "data/processed/predictions_latest.csv", "app/assets/bairros.geojson",
    "config/stations_bairros.json", "docker-compose.yml", ".env.example",
]
PORTAS = {"POSTGRES_HOST_PORT": "5433", "API_HOST_PORT": "8000", "DASHBOARD_HOST_PORT": "8501",
          "MLFLOW_HOST_PORT": "5000", "MQTT_HOST_PORT": "1883"}
LOCAIS = ("127.0.0.1", "localhost", "::1")


def check_env(valores: dict[str, str]) -> list[tuple[str, str]]:
    """Verificações puras sobre o conteúdo do .env: lista de (nível, mensagem)."""
    achados = []
    for chave in GERADORES:
        if chave == "DASHBOARD_PASSWORD" and valores.get("DASHBOARD_AUTH", "on").lower() in ("off", "0", "false", "no"):
            continue
        if e_exemplo(valores.get(chave, "")):
            achados.append(("ERRO", f"{chave} vazio ou com o texto de exemplo (rode python scripts/setup_env.py)"))
    senha = valores.get("POSTGRES_PASSWORD", "")
    if senha and not senha.lower().startswith(("troque", "gere")) and not re.fullmatch(r"[A-Za-z0-9]+", senha):
        achados.append(("ERRO", "POSTGRES_PASSWORD deve ter só letras e números (ela entra numa URL)"))
    bind = valores.get("BIND_ADDRESS", "127.0.0.1")
    if bind not in LOCAIS:
        achados.append(("AVISO", f"BIND_ADDRESS={bind}: API e dashboard ficam abertos na rede; a API não tem "
                                 "autenticação e o login do dashboard é simples (só para demonstração)"))
    if valores.get("DASHBOARD_AUTH", "on").lower() in ("off", "0", "false", "no"):
        achados.append(("AVISO", "DASHBOARD_AUTH=off: o dashboard abre sem login (só para demonstração)"))
    porta_mqtt = valores.get("MQTT_HOST_PORT", PORTAS["MQTT_HOST_PORT"])
    achados.append(("AVISO", f"Mosquitto anônimo em 0.0.0.0:{porta_mqtt} (a ESP32 precisa); use só em rede de "
                             "desenvolvimento ou demonstração"))
    return achados


def porta_ocupada(porta: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
            return True
    except OSError:
        return False


def escrever(nivel: str, texto: str) -> None:
    print(f"[{nivel:5}] {texto}")


def main() -> int:
    erros = 0

    def registrar(nivel: str, texto: str) -> None:
        nonlocal erros
        escrever(nivel, texto)
        erros += nivel == "ERRO"

    if sys.version_info < (3, 11):
        registrar("AVISO", f"Python {sys.version_info.major}.{sys.version_info.minor}: o projeto usa 3.11")
    else:
        registrar("OK", f"Python {sys.version_info.major}.{sys.version_info.minor}")
    for caminho in ARQUIVOS_MINIMOS:
        registrar("OK" if (ROOT / caminho).exists() else "ERRO", f"arquivo {caminho}")
    meta = ROOT / "models" / "model_meta.json"
    reqs = ROOT / "requirements-runtime.txt"
    if meta.exists() and reqs.exists():
        versao = json.loads(meta.read_text(encoding="utf-8")).get("sklearn_version")
        fixada = re.search(r"scikit-learn==([\d.]+)", reqs.read_text(encoding="utf-8"))
        ok = bool(fixada) and fixada.group(1) == versao
        registrar("OK" if ok else "ERRO", f"scikit-learn do modelo ({versao}) igual ao de requirements-runtime.txt")
    docker = shutil.which("docker")
    if not docker:
        registrar("ERRO", "docker não encontrado no PATH")
    else:
        pronto = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True)
        registrar("OK" if pronto.returncode == 0 else "ERRO",
                  f"docker daemon {'respondendo (' + pronto.stdout.strip() + ')' if pronto.returncode == 0 else 'não responde'}")
    env_path = ROOT / ".env"
    if not env_path.exists():
        registrar("ERRO", ".env não existe (rode python scripts/setup_env.py)")
        valores = {}
    else:
        valores = parse_env(env_path.read_text(encoding="utf-8"))
        registrar("OK", ".env encontrado")
        for nivel, texto in check_env(valores):
            registrar(nivel, texto)
    if docker and env_path.exists():
        cfg = subprocess.run([docker, "compose", "config", "-q"], cwd=ROOT, capture_output=True, text=True)
        registrar("OK" if cfg.returncode == 0 else "ERRO",
                  "docker compose config válido" if cfg.returncode == 0 else f"docker compose config: {cfg.stderr.strip()[:200]}")
    for chave, padrao in PORTAS.items():
        porta = int(valores.get(chave, padrao))
        if porta_ocupada(porta):
            registrar("AVISO", f"porta {porta} ({chave}) já está em uso (pode ser a própria pilha rodando)")
        else:
            registrar("OK", f"porta {porta} ({chave}) livre")
    print(f"\n{'Há ERROs acima.' if erros else 'Sem erros.'} Avisos não impedem de subir.")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
