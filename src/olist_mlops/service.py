"""Inference orchestration independent of HTTP."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

import pandas as pd

from .model import InferenceModel
from .monitoring import PredictionDriftMonitor, ServiceMetrics
from .schemas import OrderRequest, PredictionResponse
from .storage import PredictionLog, PredictionStore
from .validation import DataValidationError, OrderValidator

LOGGER = logging.getLogger(__name__)


class PredictionService:
    def __init__(
        self,
        *,
        model: InferenceModel,
        validator: OrderValidator,
        store: PredictionStore,
        metrics: ServiceMetrics,
        drift_monitor: PredictionDriftMonitor,
        drift_alert_threshold: float,
    ) -> None:
        self.model = model
        self.validator = validator
        self.store = store
        self.metrics = metrics
        self.drift_monitor = drift_monitor
        self.drift_alert_threshold = drift_alert_threshold

    def predict(self, orders: list[OrderRequest], *, endpoint: str) -> list[PredictionResponse]:
        records = [order.model_dump(mode="python") for order in orders]
        json_records = [order.model_dump(mode="json") for order in orders]
        frame = pd.DataFrame(records)
        started = time.perf_counter()
        try:
            self.validator.validate(frame)
            outputs = self.model.predict_frame(frame).reset_index(drop=True)
        except DataValidationError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            self.metrics.prediction_errors.labels(kind="data_validation").inc()
            for order, payload in zip(orders, json_records, strict=True):
                self._store_failure(
                    order=order,
                    payload=payload,
                    endpoint=endpoint,
                    latency_ms=latency_ms,
                    error=json.dumps(exc.failures, ensure_ascii=False),
                )
            raise

        latency_ms = (time.perf_counter() - started) * 1000
        responses: list[PredictionResponse] = []
        for order, payload, output in zip(
            orders, json_records, outputs.to_dict(orient="records"), strict=True
        ):
            request_id = str(uuid4())
            prediction = str(output["prediction"])
            probability = float(output["probability"])
            self.metrics.predictions.labels(prediction=prediction).inc()
            self.metrics.prediction_probability.observe(probability)
            rolling_ratio, drift_score = self.drift_monitor.observe(prediction)
            self.metrics.rolling_late_ratio.set(rolling_ratio)
            self.metrics.drift_score.set(drift_score)
            if drift_score >= self.drift_alert_threshold:
                LOGGER.warning(
                    "prediction_drift_alert score=%.4f rolling_late_ratio=%.4f model_version=%s",
                    drift_score,
                    rolling_ratio,
                    self.model.metadata.version,
                )
            log_record = PredictionLog(
                request_id=request_id,
                order_id=order.order_id,
                endpoint=endpoint,
                input_payload=payload,
                prediction=prediction,
                probability=probability,
                model_version=self.model.metadata.version,
                validation_status="passed",
                latency_ms=latency_ms,
            )
            self.store.save(log_record)
            LOGGER.info(
                "prediction_request request_id=%s input=%s output=%s probability=%.8f "
                "latency_ms=%.3f model_version=%s",
                request_id,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                prediction,
                probability,
                latency_ms,
                self.model.metadata.version,
            )
            responses.append(
                PredictionResponse(
                    request_id=request_id,
                    order_id=order.order_id,
                    prediction=prediction,
                    probability=probability,
                    model_version=self.model.metadata.version,
                )
            )
        return responses

    def _store_failure(
        self,
        *,
        order: OrderRequest,
        payload: dict,
        endpoint: str,
        latency_ms: float,
        error: str,
    ) -> None:
        request_id = str(uuid4())
        self.store.save(
            PredictionLog(
                request_id=request_id,
                order_id=order.order_id,
                endpoint=endpoint,
                input_payload=payload,
                prediction=None,
                probability=None,
                model_version=self.model.metadata.version,
                validation_status="failed",
                latency_ms=latency_ms,
                error=error[:1000],
            )
        )
        LOGGER.warning(
            "prediction_rejected request_id=%s input=%s latency_ms=%.3f "
            "model_version=%s validation_error=%s",
            request_id,
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            latency_ms,
            self.model.metadata.version,
            error,
        )
