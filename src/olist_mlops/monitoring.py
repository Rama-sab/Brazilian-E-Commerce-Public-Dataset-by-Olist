"""Prometheus metrics and rolling prediction-distribution drift."""

from __future__ import annotations

import threading
from collections import deque

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class ServiceMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.http_requests = Counter(
            "olist_http_requests_total",
            "HTTP requests handled by the inference service",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.http_latency = Histogram(
            "olist_http_request_latency_seconds",
            "HTTP request latency in seconds",
            ["method", "route"],
            registry=self.registry,
        )
        self.predictions = Counter(
            "olist_predictions_total",
            "Predictions by assigned class",
            ["prediction"],
            registry=self.registry,
        )
        self.prediction_probability = Histogram(
            "olist_late_probability",
            "Distribution of predicted late probabilities",
            buckets=(0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95),
            registry=self.registry,
        )
        self.prediction_errors = Counter(
            "olist_prediction_errors_total",
            "Prediction failures grouped by kind",
            ["kind"],
            registry=self.registry,
        )
        self.rolling_late_ratio = Gauge(
            "olist_prediction_rolling_late_ratio",
            "Late prediction ratio in the configured rolling window",
            registry=self.registry,
        )
        self.drift_score = Gauge(
            "olist_prediction_drift_absolute_rate_difference",
            "Absolute difference between rolling and baseline late rate",
            registry=self.registry,
        )


class PredictionDriftMonitor:
    def __init__(self, *, window_size: int, baseline_late_rate: float) -> None:
        self._values: deque[int] = deque(maxlen=window_size)
        self._baseline = baseline_late_rate
        self._lock = threading.Lock()

    def observe(self, prediction: str) -> tuple[float, float]:
        with self._lock:
            self._values.append(int(prediction == "late"))
            ratio = sum(self._values) / len(self._values)
            return ratio, abs(ratio - self._baseline)
