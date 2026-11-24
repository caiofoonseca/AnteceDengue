"""Baixa os limites dos bairros do Recife (Portal de Dados Abertos, API CKAN), simplifica e salva em
app/assets/bairros.geojson. Uso: python scripts/build_bairros_geojson.py [--tolerancia 0.00002]

Fonte: conjunto "Área urbana", recurso GeoJSON "Bairros do Recife" (licença ODbL).
A simplificação (Douglas-Peucker por anel, em graus) é só visual: não serve para cálculo de áreas.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config
from src.bairros import normalize_name

API = "https://dados.recife.pe.gov.br/api/3/action/package_show"
DATASET = "area-urbana"
RECURSO = "Bairros do Recife"
DESTINO = config.ROOT / "app" / "assets" / "bairros.geojson"
CASAS_DECIMAIS = 5


def distancia_ao_segmento(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def douglas_peucker(pontos: list, tolerancia: float) -> list:
    """Simplifica uma linha (lista de [x, y]) mantendo os extremos."""
    if len(pontos) < 3:
        return pontos
    manter = [False] * len(pontos)
    manter[0] = manter[-1] = True
    pilha = [(0, len(pontos) - 1)]
    while pilha:
        i, j = pilha.pop()
        maior, indice = 0.0, None
        for k in range(i + 1, j):
            d = distancia_ao_segmento(pontos[k], pontos[i], pontos[j])
            if d > maior:
                maior, indice = d, k
        if indice is not None and maior > tolerancia:
            manter[indice] = True
            pilha.extend([(i, indice), (indice, j)])
    return [p for p, m in zip(pontos, manter) if m]


def simplificar_anel(anel: list, tolerancia: float) -> list | None:
    simples = douglas_peucker(anel, tolerancia)
    if len(simples) < 4:
        return None
    return [[round(x, CASAS_DECIMAIS), round(y, CASAS_DECIMAIS)] for x, y in simples]


def simplificar_geometria(geom: dict, tolerancia: float) -> dict:
    poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    saida = []
    for poligono in poligonos:
        aneis = [simplificar_anel(a, tolerancia) for a in poligono]
        if aneis[0] is None:
            continue
        saida.append([a for a in aneis if a is not None])
    return {"type": "MultiPolygon", "coordinates": saida}


def baixar() -> tuple[dict, dict]:
    pacote = requests.get(API, params={"id": DATASET}, timeout=60).json()["result"]
    recurso = next(r for r in pacote["resources"] if r["name"].strip() == RECURSO and r["format"] == "GeoJSON")
    url = recurso["url"].replace(":443", "")
    for tentativa in range(6):
        resposta = requests.get(url, timeout=180)
        if resposta.status_code == 200:
            return resposta.json(), pacote
        print(f"tentativa {tentativa + 1}: HTTP {resposta.status_code}; aguardando")
        time.sleep(4)
    raise RuntimeError(f"não foi possível baixar {url}")


def converter(bruto: dict, tolerancia: float) -> dict:
    features = []
    for f in bruto["features"]:
        nome = normalize_name(f["properties"]["EBAIRRNOME"])
        features.append({"type": "Feature", "properties": {"bairro": nome},
                         "geometry": simplificar_geometria(f["geometry"], tolerancia)})
    return {"type": "FeatureCollection", "features": features}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tolerancia", type=float, default=0.00002)
    args = parser.parse_args(argv)
    bruto, pacote = baixar()
    print(f"Conjunto: {pacote['title']} | licença: {pacote['license_title']} | modificado: {pacote['metadata_modified']}")
    resultado = converter(bruto, args.tolerancia)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tamanho = DESTINO.stat().st_size / 1e6
    print(f"{len(resultado['features'])} bairros; {tamanho:.2f} MB (original {len(json.dumps(bruto)) / 1e6:.2f} MB) -> {DESTINO}")


if __name__ == "__main__":
    main()
