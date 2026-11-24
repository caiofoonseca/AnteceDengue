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
  echo "Falta o .env. Rode: python scripts/setup_env.py (gera as senhas) e depois este script de novo."
  exit 1
fi

env_val() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d '\r' || true; }
porta_dash=$(env_val DASHBOARD_HOST_PORT); porta_dash=${porta_dash:-8501}
porta_api=$(env_val API_HOST_PORT); porta_api=${porta_api:-8000}
porta_mlflow=$(env_val MLFLOW_HOST_PORT); porta_mlflow=${porta_mlflow:-5000}
usuario_dash=$(env_val DASHBOARD_USER); usuario_dash=${usuario_dash:-g15}
auth_dash=$(env_val DASHBOARD_AUTH); auth_dash=${auth_dash:-on}

porta_airflow=$(grep -E '^AIRFLOW_HOST_PORT=' .env | cut -d= -f2 || true)
porta_airflow=${porta_airflow:-8080}
COMPOSE=(docker compose)
if [ "$AIRFLOW" = 1 ]; then COMPOSE+=(--profile airflow); fi

echo "== 1/5 Subindo a pilha base =="
"${COMPOSE[@]}" up --build -d

echo "== 2/5 Conferindo o champion no MLflow =="
alias_url="http://localhost:${porta_mlflow}/api/2.0/mlflow/registered-models/alias?name=antecedengue-risk-classifier&alias=champion"
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
echo "Dashboard : http://localhost:${porta_dash}   (sensor SIMULADO)"
if [ "$auth_dash" = "off" ]; then
  echo "Login     : desligado (DASHBOARD_AUTH=off)"
else
  echo "Login     : usuário ${usuario_dash}; a senha está em DASHBOARD_PASSWORD no arquivo .env"
fi
echo "API       : http://localhost:${porta_api}/docs"
echo "MLflow    : http://localhost:${porta_mlflow}"
if [ "$AIRFLOW" = 1 ]; then echo "Airflow   : http://localhost:${porta_airflow}   (usuário e senha em AIRFLOW_ADMIN_* no .env)"; fi
echo "Para derrubar: scripts/demo.sh --down   (ou --down --volumes para apagar os dados)"
