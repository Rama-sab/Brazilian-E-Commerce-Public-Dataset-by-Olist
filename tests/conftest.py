from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def good_payload() -> dict:
    return json.loads((PROJECT_ROOT / "models/seed/example_order.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    prediction_path = tmp_path / "predictions.jsonl"
    log_path = tmp_path / "api.log"
    monkeypatch.setenv("MODEL_LOADER", "local")
    monkeypatch.setenv("PREDICTION_STORE_BACKEND", "jsonl")
    monkeypatch.setenv("PREDICTION_LOG_FILE", str(prediction_path))
    monkeypatch.setenv("APP_LOG_FILE", str(log_path))
    with TestClient(create_app(PROJECT_ROOT / "config/settings.yaml")) as test_client:
        test_client.prediction_path = prediction_path
        yield test_client
