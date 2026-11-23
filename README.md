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
