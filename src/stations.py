"""Relação estação -> bairro (config/stations_bairros.json), validada contra os bairros do painel."""
import json
from pathlib import Path

import pandas as pd

from src import config


class StationConfigError(ValueError):
    pass


def load_station_map(path: Path = config.STATIONS_PATH) -> dict[str, str]:
    dados = json.loads(path.read_text(encoding="utf-8"))
    mapa = dados.get("stations")
    if not isinstance(mapa, dict):
        raise StationConfigError(f"{path.name}: esperado o objeto \"stations\" com station_id -> bairro")
    return {str(k): str(v).strip().upper() for k, v in mapa.items()}


def load_station_coordinates(path: Path = config.STATIONS_PATH) -> dict[str, tuple[float, float]]:
    """station_id -> (latitude, longitude) do objeto "coordinates"; só estações que também estão em "stations"."""
    dados = json.loads(path.read_text(encoding="utf-8"))
    coordenadas = dados.get("coordinates")
    if not isinstance(coordenadas, dict):
        raise StationConfigError(f"{path.name}: esperado o objeto \"coordinates\" com station_id -> [latitude, longitude]")
    estacoes = dados.get("stations", {})
    resultado = {}
    for estacao in estacoes:
        valor = coordenadas.get(estacao)
        if not (isinstance(valor, (list, tuple)) and len(valor) == 2 and all(isinstance(x, (int, float)) for x in valor)):
            raise StationConfigError(f"{path.name}: a estação {estacao} não tem coordenadas [latitude, longitude]")
        resultado[str(estacao)] = (float(valor[0]), float(valor[1]))
    return resultado


def panel_bairros(panel_path: Path = config.DATA_PROCESSED / "panel.csv") -> set[str]:
    return set(pd.read_csv(panel_path, usecols=["bairro"])["bairro"].unique())


def validate_station_map(mapa: dict[str, str], bairros: set[str]) -> dict[str, str]:
    """Falha com erro claro se algum bairro do mapa não existir no painel; devolve o próprio mapa."""
    desconhecidos = {est: b for est, b in mapa.items() if b not in bairros}
    if desconhecidos:
        raise StationConfigError(
            f"bairros que não existem no painel: {desconhecidos}. Use os nomes oficiais (maiúsculas, sem acento).")
    return mapa
