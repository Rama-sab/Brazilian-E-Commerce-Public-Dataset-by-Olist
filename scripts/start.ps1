$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

docker compose --env-file .env up -d --build --wait
Write-Host "API docs: http://localhost:8000/docs"
Write-Host "MLflow: http://localhost:5000"
Write-Host "MinIO: http://localhost:9001"
Write-Host "Prometheus: http://localhost:9090"

