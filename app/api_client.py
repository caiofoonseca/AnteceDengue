"""Cliente HTTP da API do AnteceDengue. O dashboard só conversa com a API, nunca com arquivos ou com o modelo."""
import os
from urllib.parse import quote

import requests

DEFAULT_API_URL = "http://localhost:8000"


class ApiUnavailable(RuntimeError):
    """A API não respondeu (fora do ar, endereço errado ou tempo esgotado)."""

    def __init__(self, base_url: str, motivo: str):
        super().__init__(f"API fora do ar em {base_url}: {motivo}")
        self.base_url = base_url
        self.motivo = motivo


class ApiError(RuntimeError):
    """A API respondeu com erro (404, 503...). `detail` traz a mensagem da API."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def api_url() -> str:
    return os.getenv("API_URL", DEFAULT_API_URL).rstrip("/")


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or api_url()).rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        try:
            resposta = requests.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as erro:
            raise ApiUnavailable(self.base_url, type(erro).__name__) from erro
        if resposta.status_code >= 400:
            try:
                detail = resposta.json().get("detail", resposta.text)
            except ValueError:
                detail = resposta.text
            raise ApiError(resposta.status_code, str(detail))
        return resposta.json()

    def health(self) -> dict:
        return self.get("/health")

    def model(self) -> dict:
        return self.get("/model")

    def predictions(self, top: int | None = None, classe: str | None = None) -> dict:
        params = {k: v for k, v in (("top", top), ("classe", classe)) if v is not None}
        return self.get("/predictions/latest", params)

    def bairros(self) -> dict:
        return self.get("/bairros")

    def bairro(self, nome: str) -> dict:
        return self.get(f"/bairros/{quote(nome, safe='')}")

    def sensor_weekly(self, bairro: str | None = None, desde: str | None = None) -> dict:
        params = {k: v for k, v in (("bairro", bairro), ("desde", desde)) if v is not None}
        return self.get("/sensor/weekly", params)
