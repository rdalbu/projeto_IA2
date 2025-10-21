Param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000
)

Write-Host "==> Preparando ambiente Python (venv .venv)" -ForegroundColor Cyan
if (-not (Test-Path .venv)) {
  py -m venv .venv 2>$null
  if ($LASTEXITCODE -ne 0) { python -m venv .venv }
}

$activate = Join-Path (Resolve-Path .venv).Path 'Scripts\Activate.ps1'
if (Test-Path $activate) { . $activate } else { Write-Error "Falha ao ativar venv (.venv)."; exit 1 }

Write-Host "==> Instalando dependências (requirements.txt)" -ForegroundColor Cyan
pip install --upgrade pip > $null
pip install -r requirements.txt

Write-Host "==> Iniciando API em http://${BindHost}:$Port/front" -ForegroundColor Green
Start-Process "http://${BindHost}:$Port/front" | Out-Null

uvicorn src.detector_gestos.api:app --host $BindHost --port $Port --reload
