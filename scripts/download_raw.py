"""Baixa os CSVs anuais de dengue (2013-2025) do Portal de Dados Abertos do Recife.

Usa a API CKAN do portal para descobrir as URLs reais dos recursos.
Uso: python scripts/download_raw.py
"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402

API = "https://dados.recife.pe.gov.br/api/3/action/package_show"
DATASET = "casos-de-dengue-zika-e-chikungunya"
ANOS = range(2013, 2026)


def main() -> None:
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    aux = config.DATA_RAW / "auxiliares"
    aux.mkdir(exist_ok=True)

    pkg = requests.get(API, params={"id": DATASET}, timeout=60).json()["result"]
    print(f"Conjunto: {pkg['title']} | licença: {pkg['license_title']}")

    achados = {}
    for r in pkg["resources"]:
        nome = r["name"].strip()
        m = re.fullmatch(r"Casos de Dengue (?:em )?(\d{4})", nome)
        if m and int(m.group(1)) in ANOS:
            achados[int(m.group(1))] = r
        elif nome in ("Tabela de Bairros", "Metadados dos Casos Confirmados de Dengue 2013-2015",
                      "Metadados dos Casos Confirmados de Dengue a partir de 2016"):
            destino = aux / re.sub(r"\W+", "_", nome.lower()).strip("_")
            destino = destino.with_suffix("." + r["format"].lower())
            destino.write_bytes(requests.get(r["url"], timeout=120).content)
            print(f"auxiliar: {destino.name}")

    faltando = [a for a in ANOS if a not in achados]
    if faltando:
        print(f"ATENÇÃO: anos não encontrados no portal: {faltando}")
    for ano, r in sorted(achados.items()):
        destino = config.DATA_RAW / f"dengue_{ano}.csv"
        resp = requests.get(r["url"], timeout=300)
        resp.raise_for_status()
        destino.write_bytes(resp.content)
        print(f"{ano}: {len(resp.content) / 1e6:.1f} MB -> {destino.name}")


if __name__ == "__main__":
    main()
