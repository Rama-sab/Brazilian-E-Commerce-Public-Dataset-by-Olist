from __future__ import annotations

import json

import pytest


@pytest.mark.integration
def test_health_and_model_routes(client) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "model_ready": True,
        "prediction_store_ready": True,
    }

    model = client.get("/v1/model")
    assert model.status_code == 200
    assert model.json()["source"] == "local_artifacts"
    assert model.json()["transformed_feature_count"] == 142


@pytest.mark.integration
def test_single_prediction_end_to_end(client, good_payload: dict) -> None:
    response = client.post("/v1/predict", json=good_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] == "on_time"
    assert body["probability"] == pytest.approx(0.5451138144592078, abs=1e-14)
    assert body["model_version"] == "attached-task2-v1"
    assert body["validation_status"] == "passed"

    rows = [json.loads(line) for line in client.prediction_path.read_text().splitlines()]
    assert rows[-1]["request_id"] == body["request_id"]
    assert rows[-1]["latency_ms"] >= 0
    assert rows[-1]["model_version"] == body["model_version"]


@pytest.mark.integration
def test_nullable_integer_features_are_accepted(client, good_payload: dict) -> None:
    payload = dict(
        good_payload,
        payment_count=None,
        max_payment_installments=None,
        payment_type_count=None,
    )
    response = client.post("/v1/predict", json=payload)
    assert response.status_code == 200
    assert response.json()["prediction"] in {"late", "on_time"}


@pytest.mark.integration
def test_batch_prediction_and_metrics(client, good_payload: dict) -> None:
    second = dict(good_payload, order_id="demo-order-002")
    response = client.post("/v1/predict/batch", json={"orders": [good_payload, second]})
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert len(response.json()["predictions"]) == 2

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "olist_http_requests_total" in metrics.text
    assert "olist_predictions_total" in metrics.text
    assert "olist_prediction_drift_absolute_rate_difference" in metrics.text


@pytest.mark.integration
def test_bad_payload_is_rejected_and_logged(client, good_payload: dict) -> None:
    invalid_category = dict(good_payload, payment_type_mode="cryptocurrency")
    response = client.post("/v1/predict", json=invalid_category)
    assert response.status_code == 422
    assert response.json()["policy"] == "reject"
    assert response.json()["validation_failures"]

    missing_required = dict(good_payload)
    missing_required.pop("total_price")
    schema_response = client.post("/v1/predict", json=missing_required)
    assert schema_response.status_code == 422
    assert schema_response.json()["policy"] == "reject"

    rows = [json.loads(line) for line in client.prediction_path.read_text().splitlines()]
    assert {row["validation_status"] for row in rows}.issuperset(
        {"failed", "request_schema_failed"}
    )
