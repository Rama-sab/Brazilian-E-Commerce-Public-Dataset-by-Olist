"""FastAPI entry point for the Olist inference service."""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from olist_mlops.config import Settings, load_settings, load_yaml
from olist_mlops.logging_utils import configure_logging
from olist_mlops.model import InferenceModel, load_inference_model
from olist_mlops.monitoring import PredictionDriftMonitor, ServiceMetrics
from olist_mlops.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    ModelInfoResponse,
    OrderRequest,
    PredictionResponse,
)
from olist_mlops.service import PredictionService
from olist_mlops.storage import PredictionLog, PredictionStore, create_prediction_store
from olist_mlops.validation import DataValidationError, OrderValidator

LOGGER = logging.getLogger(__name__)


@dataclass
class AppServices:
    settings: Settings
    model: InferenceModel
    store: PredictionStore
    prediction_service: PredictionService


def create_app(config_path: str | Path | None = None) -> FastAPI:
    bootstrap_settings = load_settings(config_path)
    metrics = ServiceMetrics()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        settings = load_settings(config_path)
        configure_logging(settings)
        contract = load_yaml(settings.path("paths.feature_contract"))
        model = load_inference_model(settings)
        store = create_prediction_store(settings)
        validator = OrderValidator(contract)
        drift = PredictionDriftMonitor(
            window_size=int(settings.get("monitoring.rolling_window")),
            baseline_late_rate=float(settings.get("monitoring.baseline_late_rate")),
        )
        prediction_service = PredictionService(
            model=model,
            validator=validator,
            store=store,
            metrics=metrics,
            drift_monitor=drift,
            drift_alert_threshold=float(settings.get("monitoring.drift_absolute_rate_threshold")),
        )
        application.state.services = AppServices(
            settings=settings,
            model=model,
            store=store,
            prediction_service=prediction_service,
        )
        LOGGER.info(
            "service_started environment=%s model_name=%s model_version=%s source=%s",
            settings.get("service.environment"),
            model.metadata.name,
            model.metadata.version,
            model.metadata.source,
        )
        yield
        engine = getattr(store, "engine", None)
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title=str(bootstrap_settings.get("service.name")),
        summary="Predict whether a new Olist order will arrive late.",
        version=str(bootstrap_settings.get("service.version")),
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def observe_http(request: Request, call_next):
        started = time.perf_counter()
        response_status = 500
        try:
            response = await call_next(request)
            response_status = response.status_code
            return response
        finally:
            route = request.url.path
            metrics.http_requests.labels(
                method=request.method, route=route, status=str(response_status)
            ).inc()
            metrics.http_latency.labels(method=request.method, route=route).observe(
                time.perf_counter() - started
            )

    @application.exception_handler(DataValidationError)
    async def handle_data_validation(request: Request, exc: DataValidationError) -> JSONResponse:
        current = getattr(request.app.state, "services", None)
        policy = (
            current.settings.get("validation.failure_policy")
            if current is not None
            else bootstrap_settings.get("validation.failure_policy")
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Incoming order failed the data contract",
                "validation_failures": jsonable_encoder(exc.failures),
                "policy": policy,
            },
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        metrics.prediction_errors.labels(kind="request_schema").inc()
        body = jsonable_encoder(exc.body) if exc.body is not None else {}
        LOGGER.warning(
            "request_schema_rejected path=%s input=%s errors=%s",
            request.url.path,
            json.dumps(body, ensure_ascii=False, sort_keys=True),
            json.dumps(jsonable_encoder(exc.errors()), ensure_ascii=False),
        )
        services = getattr(request.app.state, "services", None)
        policy = (
            services.settings.get("validation.failure_policy")
            if services is not None
            else bootstrap_settings.get("validation.failure_policy")
        )
        if services is not None and request.url.path.startswith("/v1/predict"):
            services.store.save(
                PredictionLog(
                    request_id=str(uuid4()),
                    order_id=body.get("order_id") if isinstance(body, dict) else None,
                    endpoint=request.url.path,
                    input_payload=body if isinstance(body, dict) else {"body": body},
                    prediction=None,
                    probability=None,
                    model_version=services.model.metadata.version,
                    validation_status="request_schema_failed",
                    latency_ms=0.0,
                    error=json.dumps(jsonable_encoder(exc.errors()), ensure_ascii=False)[:1000],
                )
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": jsonable_encoder(exc.errors()), "policy": policy},
        )

    def services(request: Request) -> AppServices:
        return request.app.state.services

    @application.get("/health", response_model=HealthResponse, tags=["operations"])
    def health(request: Request) -> HealthResponse:
        current = services(request)
        store_ready = current.store.is_ready()
        return HealthResponse(
            status="ok" if store_ready else "degraded",
            model_ready=current.model is not None,
            prediction_store_ready=store_ready,
        )

    @application.get("/v1/model", response_model=ModelInfoResponse, tags=["model"])
    def model_info(request: Request) -> ModelInfoResponse:
        metadata = services(request).model.metadata
        return ModelInfoResponse(
            name=metadata.name,
            version=metadata.version,
            stage=metadata.stage,
            alias=metadata.alias,
            source=metadata.source,
            decision_threshold=metadata.decision_threshold,
            transformed_feature_count=metadata.transformed_feature_count,
        )

    @application.post(
        "/v1/predict",
        response_model=PredictionResponse,
        tags=["prediction"],
    )
    def predict(order: OrderRequest, request: Request) -> PredictionResponse:
        return services(request).prediction_service.predict([order], endpoint="/v1/predict")[0]

    @application.post(
        "/v1/predict/batch",
        response_model=BatchPredictionResponse,
        tags=["prediction"],
    )
    def predict_batch(payload: BatchPredictionRequest, request: Request) -> BatchPredictionResponse:
        current = services(request)
        maximum = int(current.settings.get("service.batch_max_size"))
        if len(payload.orders) > maximum:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Batch size exceeds configured maximum of {maximum}",
            )
        predictions = current.prediction_service.predict(
            payload.orders, endpoint="/v1/predict/batch"
        )
        return BatchPredictionResponse(
            predictions=predictions,
            count=len(predictions),
            model_version=current.model.metadata.version,
        )

    @application.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        return Response(
            content=generate_latest(metrics.registry),
            media_type=CONTENT_TYPE_LATEST,
        )

    return application


app = create_app()
