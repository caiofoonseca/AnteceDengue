param([switch]$Airflow, [switch]$Down, [switch]$Volumes)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Compose {
    & docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose falhou: $args" }
}

$perfis = @("--profile", "demo", "--profile", "init", "--profile", "train", "--profile", "airflow")

if ($Down) {
    if ($Volumes) {
        Invoke-Compose @perfis down -v --remove-orphans
        Write-Host "Tudo derrubado e volumes apagados (banco, MLflow, Mosquitto, logs do Airflow)."
    } else {
        Invoke-Compose @perfis down --remove-orphans
        Write-Host "Tudo derrubado; os volumes foram mantidos. Use -Down -Volumes para apagá-los."
    }
    return
}

if (-not (Test-Path .env)) {
    Write-Host "Falta o .env. Rode: python scripts/setup_env.py (gera as senhas) e depois este script de novo."
    exit 1
}

function Get-EnvValue($chave, $padrao) {
    $linha = Select-String -Path .env -Pattern "^$chave=(.+)$" | Select-Object -First 1
    if ($linha) { return $linha.Matches[0].Groups[1].Value.Trim() }
    return $padrao
}
$portaDash = Get-EnvValue "DASHBOARD_HOST_PORT" "8501"
$portaApi = Get-EnvValue "API_HOST_PORT" "8000"
$portaMlflow = Get-EnvValue "MLFLOW_HOST_PORT" "5000"
$usuarioDash = Get-EnvValue "DASHBOARD_USER" "g15"
$authDash = Get-EnvValue "DASHBOARD_AUTH" "on"

$portaAirflow = "8080"
$linha = Select-String -Path .env -Pattern '^AIRFLOW_HOST_PORT=(.+)$' | Select-Object -First 1
if ($linha) { $portaAirflow = $linha.Matches[0].Groups[1].Value.Trim() }
$usuarioPg = "antecedengue"
$linha = Select-String -Path .env -Pattern '^POSTGRES_USER=(.+)$' | Select-Object -First 1
if ($linha) { $usuarioPg = $linha.Matches[0].Groups[1].Value.Trim() }

$base = @()
if ($Airflow) { $base += @("--profile", "airflow") }

Write-Host "== 1/5 Subindo a pilha base =="
Invoke-Compose @base up --build -d

Write-Host "== 2/5 Conferindo o champion no MLflow =="
$aliasUrl = "http://localhost:$portaMlflow/api/2.0/mlflow/registered-models/alias?name=antecedengue-risk-classifier&alias=champion"
$existe = $false
try { $null = Invoke-WebRequest -Uri $aliasUrl -UseBasicParsing -TimeoutSec 10; $existe = $true } catch { $existe = $false }
if ($existe) {
    Write-Host "champion já existe; seed não necessário"
} else {
    Invoke-Compose @base --profile init run --rm seed-mlflow
    Write-Host "== 3/5 Reiniciando a API para carregar o modelo do Registry =="
    Invoke-Compose @base restart api
}

Write-Host "== 4/5 Subindo o simulador de sensor (SENSOR_FONTE=simulado) =="
$env:SENSOR_FONTE = "simulado"
try {
    Invoke-Compose @base --profile demo up -d
} finally {
    Remove-Item Env:SENSOR_FONTE -ErrorAction SilentlyContinue
}
for ($i = 0; $i -lt 20; $i++) {
    $n = (& docker compose @base exec -T postgres psql -U $usuarioPg -tAc "select count(*) from sensor_readings where is_valid" 2>$null)
    if ($n -and [int]$n -gt 0) { break }
    Start-Sleep -Seconds 3
}
Invoke-Compose @base exec -T api python -m src.sensor_agg | Out-Null

Write-Host "== 5/5 Pronto =="
Write-Host "Dashboard : http://localhost:$portaDash   (sensor SIMULADO)"
if ($authDash -eq "off") {
    Write-Host "Login     : desligado (DASHBOARD_AUTH=off)"
} else {
    Write-Host "Login     : usuário $usuarioDash; a senha está em DASHBOARD_PASSWORD no arquivo .env"
}
Write-Host "API       : http://localhost:$portaApi/docs"
Write-Host "MLflow    : http://localhost:$portaMlflow"
if ($Airflow) { Write-Host "Airflow   : http://localhost:$portaAirflow   (usuário e senha em AIRFLOW_ADMIN_* no .env)" }
Write-Host "Para derrubar: scripts\demo.ps1 -Down   (ou -Down -Volumes para apagar os dados)"
