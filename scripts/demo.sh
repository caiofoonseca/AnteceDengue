#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

AIRFLOW=0; DOWN=0; VOLUMES=0
for arg in "$@"; do
  case "$arg" in
    --airflow) AIRFLOW=1 ;;
    --down) DOWN=1 ;;
    --volumes) VOLUMES=1 ;;
    *) echo "argumento desconhecido: $arg"; echo "uso: $0 [--airflow] | $0 --down [--volumes]"; exit 2 ;;
  esac
done

PERFIS=(--profile demo --profile init --profile train --profile airflow)

if [ "$DOWN" = 1 ]; then
  if [ "$VOLUMES" = 1 ]; then
    docker compose "${PERFIS[@]}" down -v --remove-orphans
    echo "Tudo derrubado e volumes apagados (banco, MLflow, Mosquitto, logs do Airflow)."
  else
    docker compose "${PERFIS[@]}" down --remove-orphans
    echo "Tudo derrubado; os volumes foram mantidos. Use --down --volumes para apagá-los."
  fi
  exit 0
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Criei o .env a partir de .env.example. Edite as senhas (POSTGRES_PASSWORD, AIRFLOW_*) e rode de novo."
  exit 1
fi

porta_airflow=$(grep -E '^AIRFLOW_HOST_PORT=' .env | cut -d= -f2 || true)
porta_airflow=${porta_airflow:-8080}
COMPOSE=(docker compose)
if [ "$AIRFLOW" = 1 ]; then COMPOSE+=(--profile airflow); fi

echo "== 1/5 Subindo a pilha base =="
"${COMPOSE[@]}" up --build -d

echo "== 2/5 Conferindo o champion no MLflow =="
alias_url="http://localhost:5000/api/2.0/mlflow/registered-models/alias?name=antecedengue-risk-classifier&alias=champion"
if curl -fsS "$alias_url" >/dev/null 2>&1; then
  echo "champion já existe; seed não necessário"
else
  "${COMPOSE[@]}" --profile init run --rm seed-mlflow
  echo "== 3/5 Reiniciando a API para carregar o modelo do Registry =="
  "${COMPOSE[@]}" restart api
fi

echo "== 4/5 Subindo o simulador de sensor (SENSOR_FONTE=simulado) =="
SENSOR_FONTE=simulado "${COMPOSE[@]}" --profile demo up -d
for _ in $(seq 1 20); do
  n=$("${COMPOSE[@]}" exec -T postgres psql -U "${POSTGRES_USER:-antecedengue}" -tAc "select count(*) from sensor_readings where is_valid" 2>/dev/null || echo 0)
  [ "${n:-0}" -gt 0 ] && break
  sleep 3
done
"${COMPOSE[@]}" exec -T api python -m src.sensor_agg >/dev/null

echo "== 5/5 Pronto =="
echo "Dashboard : http://localhost:8501   (sensor SIMULADO)"
echo "API       : http://localhost:8000/docs"
echo "MLflow    : http://localhost:5000"
if [ "$AIRFLOW" = 1 ]; then echo "Airflow   : http://localhost:${porta_airflow}   (usuário e senha em AIRFLOW_ADMIN_* no .env)"; fi
echo "Para derrubar: scripts/demo.sh --down   (ou --down --volumes para apagar os dados)"
