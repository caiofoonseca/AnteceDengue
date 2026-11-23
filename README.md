# AnteceDengue
Previsão de risco de dengue por bairro do Recife (ML + MLOps) — Projeto G15, CESAR School

## Como rodar localmente

Requer Python 3.11.

```powershell
# 1. criar o ambiente virtual
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

# 2. instalar as dependências
pip install -r requirements.txt

# 3. copiar as variáveis de ambiente (opcional em desenvolvimento)
copy .env.example .env

# 4. rodar os testes
pytest
```

## Experimentos de ML (MLflow)

Pré-requisito: `data/processed/panel.csv` e `data/processed/clima_semanal.csv` (ver `docs/DADOS.md`: `python scripts/build_panel.py` e `python scripts/build_clima.py`).

```powershell
python -m src.train --exp 01                 # 01-baseline: regressão logística + persistência
python -m src.train --exp 02                 # 02-comparacao-modelos: 6 candidatos + persistência
python -m src.train --exp 02 --no-mlflow     # roda sem registrar no MLflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Saídas: `reports/metricas_comparacao.csv` (experimento 02), `reports/metricas_baseline.csv` (experimento 01), `reports/importancia_rf.csv` e figuras em `reports/figuras/`. Os experimentos treinam no treino e avaliam na validação; o conjunto de teste fica bloqueado em código (`TestSetLocked`).
