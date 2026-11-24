FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements-runtime.txt .
RUN pip install -r requirements-runtime.txt

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data/processed /app/models /app/reports /mlflow \
    && chown -R app:app /app /mlflow

COPY --chown=app:app config ./config
COPY --chown=app:app src ./src
COPY --chown=app:app api ./api
COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts

USER app

EXPOSE 8000 8501 5000

CMD ["python", "-c", "print('Informe o comando do serviço no docker-compose.yml')"]
