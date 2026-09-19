$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:MODEL_LOADER = "local"
$env:PREDICTION_STORE_BACKEND = "jsonl"
$env:PREDICTION_LOG_FILE = "prediction_logs/test.jsonl"

ruff check .
ruff format --check .
pytest

