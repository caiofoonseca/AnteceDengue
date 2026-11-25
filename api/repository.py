"""Camada de acesso a dados da API (arquivos CSV e banco do sensor).

Os endpoints só falam com a classe Repository. Para trocar o CSV por uma tabela no Postgres, basta
reescrever os métodos daqui, sem mexer nos endpoints.
"""
import difflib
import json
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine

from src import config
from src.bairros import normalize_name
from src.db import init_db, load_latest_predictions, normalize_database_url, sensor_weekly

log = logging.getLogger("api.repository")


class PredictionsUnavailable(RuntimeError):
    pass


class PanelUnavailable(RuntimeError):
    pass


class SensorDbUnavailable(RuntimeError):
    pass


class ProjectionUnavailable(RuntimeError):
    pass


def make_engine(url: str) -> Engine:
    url = normalize_database_url(url)
    argumentos = {"connect_args": {"connect_timeout": 2}} if url.startswith("postgresql") else {}
    return create_engine(url, pool_pre_ping=True, future=True, **argumentos)


class Repository:
    def __init__(self, panel_path: Path = config.PANEL_PATH, predictions_path: Path = config.PREDICTIONS_PATH,
                 database_url: str | None = None, engine: Engine | None = None,
                 projection_path: Path = config.PROJECTION_PATH, projection_meta_path: Path = config.PROJECTION_META_PATH):
        self.projection_path = Path(projection_path)
        self.projection_meta_path = Path(projection_meta_path)
        self.panel_path = Path(panel_path)
        self.predictions_path = Path(predictions_path)
        self.engine = engine if engine is not None else make_engine(database_url or config.DATABASE_URL)
        self._cache: dict[str, tuple[float, pd.DataFrame]] = {}
        self._tables_ready = False
        self.predictions_source: str | None = None

    def _read_csv(self, caminho: Path, chave: str, erro: type[RuntimeError], mensagem: str) -> pd.DataFrame:
        if not caminho.exists():
            raise erro(mensagem)
        mtime = caminho.stat().st_mtime
        guardado = self._cache.get(chave)
        if guardado is None or guardado[0] != mtime:
            colunas_data = ["week_start", "target_week"] if chave == "predictions" else ["week_start"]
            df = pd.read_csv(caminho)
            for coluna in colunas_data:
                if coluna in df.columns:
                    df[coluna] = pd.to_datetime(df[coluna]).dt.date
            guardado = (mtime, df)
            self._cache[chave] = guardado
        return guardado[1]

    def panel(self) -> pd.DataFrame:
        return self._read_csv(self.panel_path, "panel", PanelUnavailable,
                              f"Painel de casos não encontrado em {self.panel_path.name}. Rode scripts/build_panel.py.")

    def _predictions_from_db(self) -> pd.DataFrame | None:
        """Previsões gravadas no Postgres pelo DAG semanal; None se o banco não responde ou está vazio."""
        try:
            if not self._tables_ready:
                init_db(self.engine)
                self._tables_ready = True
            df = load_latest_predictions(self.engine)
        except Exception as erro:
            log.warning("previsões no banco indisponíveis (%s); usando o CSV", type(erro).__name__)
            return None
        return None if df.empty else df

    def predictions(self) -> pd.DataFrame:
        """Banco primeiro; se não houver previsões lá, o CSV gerado por python -m src.predict_batch."""
        do_banco = self._predictions_from_db()
        if do_banco is not None:
            self.predictions_source = "postgres"
            return do_banco
        self.predictions_source = "csv"
        return self._read_csv(self.predictions_path, "predictions", PredictionsUnavailable,
                              f"Arquivo de previsões {self.predictions_path.name} não encontrado. "
                              "Gere-o com: python -m src.predict_batch")

    def predictions_available(self) -> bool:
        return self.predictions_path.exists() or self._predictions_from_db() is not None

    def bairros(self) -> list[str]:
        return sorted(self.panel()["bairro"].unique())

    def resolve_bairro(self, nome: str) -> str | None:
        """Nome oficial do bairro, sem diferença de maiúsculas, acentos e pontuação; None se não existir."""
        chave = normalize_name(nome)
        mapa = {normalize_name(b): b for b in self.bairros()}
        return mapa.get(chave)

    def suggest_bairros(self, nome: str) -> list[str]:
        chave = normalize_name(nome) or ""
        mapa = {normalize_name(b): b for b in self.bairros()}
        return [mapa[k] for k in difflib.get_close_matches(chave, list(mapa), n=3, cutoff=0.6)]

    def projection(self) -> pd.DataFrame:
        return self._read_csv(self.projection_path, "projection", ProjectionUnavailable,
                              f"Projeção não encontrada em {self.projection_path.name}. Rode python -m src.projecao.")

    def projection_meta(self) -> dict:
        if not self.projection_meta_path.exists():
            raise ProjectionUnavailable(f"Metadados da projeção não encontrados em {self.projection_meta_path.name}.")
        return json.loads(self.projection_meta_path.read_text(encoding="utf-8"))

    def latest_prediction(self, bairro: str) -> dict | None:
        try:
            df = self.predictions()
        except PredictionsUnavailable:
            return None
        linha = df[df["bairro"] == bairro]
        return None if linha.empty else linha.iloc[0].to_dict()

    def weekly_cases(self, bairro: str, weeks: int = config.API_RECENT_WEEKS) -> list[dict]:
        df = self.panel()
        recorte = df[df["bairro"] == bairro].sort_values("week_start").tail(weeks)
        return recorte[["week_start", "casos"]].to_dict("records")

    def sensor_db_ok(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as erro:
            log.warning("banco do sensor indisponível: %s", type(erro).__name__)
            return False

    def sensor_weekly(self, bairro: str | None = None, desde=None) -> list[dict]:
        try:
            if not self._tables_ready:
                init_db(self.engine)
                self._tables_ready = True
            consulta = select(sensor_weekly).order_by(sensor_weekly.c.bairro, sensor_weekly.c.week_start)
            if bairro is not None:
                consulta = consulta.where(sensor_weekly.c.bairro == bairro)
            if desde is not None:
                consulta = consulta.where(sensor_weekly.c.week_start >= desde)
            with self.engine.connect() as conn:
                return [dict(linha) for linha in conn.execute(consulta).mappings().all()]
        except Exception as erro:
            raise SensorDbUnavailable(f"Banco do sensor indisponível ({type(erro).__name__}).") from erro
