"""Cria (ou completa) o arquivo .env a partir do .env.example, gerando os segredos que ainda são texto de exemplo.

Uso:
    python scripts/setup_env.py
    python scripts/setup_env.py --set API_HOST_PORT=18000 --set DASHBOARD_HOST_PORT=18501

Valores já preenchidos no .env nunca são trocados. Os segredos gerados não são impressos: o script só diz quais
chaves foram criadas. A senha do Postgres usa só letras e números (ela entra numa URL).
"""
import argparse
import base64
import secrets
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALFANUM = string.ascii_letters + string.digits
PREFIXOS_EXEMPLO = ("troque", "gere", "change", "changeme")


def alfanumerico(tamanho: int):
    return lambda: "".join(secrets.choice(ALFANUM) for _ in range(tamanho))


GERADORES = {
    "POSTGRES_PASSWORD": alfanumerico(24),
    "AIRFLOW_ADMIN_PASSWORD": alfanumerico(20),
    "AIRFLOW_FERNET_KEY": lambda: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "AIRFLOW_SECRET_KEY": lambda: secrets.token_hex(32),
    "DASHBOARD_PASSWORD": alfanumerico(16),
}


def parse_env(texto: str) -> dict[str, str]:
    valores = {}
    for linha in texto.splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            valores[chave.strip()] = valor.strip()
    return valores


def e_exemplo(valor: str) -> bool:
    return not valor or valor.lower().startswith(PREFIXOS_EXEMPLO)


def build_env(exemplo: str, atual: str = "", ajustes: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """Devolve o texto do novo .env e a lista de chaves de segredo geradas (nunca os valores)."""
    existentes = parse_env(atual)
    ajustes = ajustes or {}
    geradas, linhas, vistas = [], [], set()
    for linha in exemplo.splitlines():
        bruta = linha.strip()
        if not bruta or bruta.startswith("#") or "=" not in bruta:
            linhas.append(linha)
            continue
        chave, valor_exemplo = (x.strip() for x in bruta.split("=", 1))
        vistas.add(chave)
        if chave in ajustes:
            valor = ajustes[chave]
        elif chave in existentes and not (chave in GERADORES and e_exemplo(existentes[chave])):
            valor = existentes[chave]
        elif chave in GERADORES and e_exemplo(valor_exemplo):
            valor = GERADORES[chave]()
            geradas.append(chave)
        else:
            valor = valor_exemplo
        linhas.append(f"{chave}={valor}")
    extras = [f"{k}={v}" for k, v in existentes.items() if k not in vistas]
    if extras:
        linhas += ["", "# valores que já estavam no .env e não constam no .env.example", *extras]
    return "\n".join(linhas).rstrip("\n") + "\n", geradas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", default=str(ROOT / ".env"), help="caminho do .env (padrão: raiz do projeto)")
    parser.add_argument("--set", action="append", default=[], metavar="CHAVE=VALOR", help="força um valor (repetível)")
    args = parser.parse_args(argv)
    ajustes = {}
    for item in args.set:
        if "=" not in item:
            parser.error(f"use CHAVE=VALOR, recebi {item!r}")
        chave, valor = item.split("=", 1)
        ajustes[chave.strip()] = valor.strip()
    destino = Path(args.env)
    exemplo = (ROOT / ".env.example").read_text(encoding="utf-8")
    atual = destino.read_text(encoding="utf-8") if destino.exists() else ""
    texto, geradas = build_env(exemplo, atual, ajustes)
    destino.write_text(texto, encoding="utf-8")
    print(f"{'Atualizei' if atual else 'Criei'} {destino}.")
    if geradas:
        print("Segredos gerados (valores só no arquivo, não impressos): " + ", ".join(geradas))
    else:
        print("Nenhum segredo novo: os valores existentes foram mantidos.")
    usuario = parse_env(texto).get("DASHBOARD_USER", "g15")
    print(f"Login do dashboard: usuário {usuario}; a senha está em DASHBOARD_PASSWORD no .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
