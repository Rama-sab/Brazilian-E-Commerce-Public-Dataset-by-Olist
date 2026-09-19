"""Durable prediction-log storage for later outcome evaluation."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from .config import Settings


@dataclass(frozen=True)
class PredictionLog:
    request_id: str
    order_id: str | None
    endpoint: str
    input_payload: dict[str, Any]
    prediction: str | None
    probability: float | None
    model_version: str
    validation_status: str
    latency_ms: float
    error: str | None = None
    actual_delivery_timestamp: str | None = None
    actual_late: bool | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PredictionStore(Protocol):
    def save(self, record: PredictionLog) -> None: ...

    def is_ready(self) -> bool: ...


class JsonlPredictionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def save(self, record: PredictionLog) -> None:
        payload = asdict(record)
        payload["created_at"] = record.created_at.isoformat()
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def is_ready(self) -> bool:
        return self.path.parent.exists()


def _prediction_table(metadata: MetaData, name: str) -> Table:
    return Table(
        name,
        metadata,
        Column("request_id", String(36), primary_key=True),
        Column("order_id", String(128), nullable=True, index=True),
        Column("endpoint", String(64), nullable=False),
        Column("input_payload", JSON, nullable=False),
        Column("prediction", String(32), nullable=True, index=True),
        Column("probability", Float, nullable=True),
        Column("model_version", String(128), nullable=False, index=True),
        Column("validation_status", String(32), nullable=False, index=True),
        Column("latency_ms", Float, nullable=False),
        Column("error", String(1000), nullable=True),
        Column("actual_delivery_timestamp", String(64), nullable=True),
        Column("actual_late", Boolean, nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, index=True),
    )


class SqlPredictionStore:
    def __init__(self, database_url: str, table_name: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        self.metadata = MetaData()
        self.table = _prediction_table(self.metadata, table_name)
        self.metadata.create_all(self.engine)

    def save(self, record: PredictionLog) -> None:
        with self.engine.begin() as connection:
            connection.execute(insert(self.table).values(**asdict(record)))

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(select(1))
            return True
        except Exception:
            return False


def create_prediction_store(settings: Settings) -> PredictionStore:
    backend = str(settings.get("prediction_store.backend")).lower()
    if backend == "postgresql":
        return SqlPredictionStore(
            database_url=str(settings.get("prediction_store.database_url")),
            table_name=str(settings.get("prediction_store.table_name")),
        )
    if backend == "jsonl":
        return JsonlPredictionStore(settings.path("paths.prediction_log_file"))
    raise ValueError(f"Unsupported prediction-store backend: {backend}")
