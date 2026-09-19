"""Pydantic request and response contracts for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

StateCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
Category = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class OrderRequest(BaseModel):
    """Prediction-time order attributes available before delivery."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "order_id": "demo-order-001",
                "order_purchase_timestamp": "2018-06-21T08:41:07",
                "order_estimated_delivery_date": "2018-07-04T00:00:00",
                "item_count": 1,
                "product_count": 1,
                "seller_count": 1,
                "total_price": 55.0,
                "total_freight": 7.65,
                "avg_item_price": 55.0,
                "max_item_price": 55.0,
                "product_category_count": 1,
                "product_name_length_mean": 59.0,
                "product_description_length_mean": 160.0,
                "product_photos_qty_mean": 5.0,
                "product_weight_g_mean": 200.0,
                "product_volume_cm3_mean": 640.0,
                "payment_count": 1,
                "payment_value_total": 62.65,
                "max_payment_installments": 1,
                "payment_type_count": 1,
                "customer_seller_distance_km": 10.8846,
                "customer_state": "SP",
                "seller_state_mode": "SP",
                "product_category_mode": "watches_gifts",
                "payment_type_mode": "boleto",
            }
        },
    )

    order_id: str | None = Field(default=None, max_length=128)
    order_purchase_timestamp: datetime
    order_estimated_delivery_date: datetime

    item_count: int = Field(ge=1)
    product_count: int = Field(ge=1)
    seller_count: int = Field(ge=1)
    total_price: float = Field(ge=0, allow_inf_nan=False)
    total_freight: float = Field(ge=0, allow_inf_nan=False)
    avg_item_price: float = Field(ge=0, allow_inf_nan=False)
    max_item_price: float = Field(ge=0, allow_inf_nan=False)
    product_category_count: int = Field(ge=0)

    product_name_length_mean: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    product_description_length_mean: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    product_photos_qty_mean: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    product_weight_g_mean: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    product_volume_cm3_mean: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    payment_count: int | None = Field(default=None, ge=1)
    payment_value_total: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    max_payment_installments: int | None = Field(default=None, ge=0)
    payment_type_count: int | None = Field(default=None, ge=1)
    customer_seller_distance_km: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    customer_state: StateCode
    seller_state_mode: StateCode
    product_category_mode: Category
    payment_type_mode: Category

    @model_validator(mode="after")
    def validate_business_relationships(self) -> OrderRequest:
        if self.order_estimated_delivery_date < self.order_purchase_timestamp:
            raise ValueError("estimated delivery must not be before purchase")
        if self.product_count > self.item_count:
            raise ValueError("product_count cannot exceed item_count")
        if self.seller_count > self.item_count:
            raise ValueError("seller_count cannot exceed item_count")
        if self.max_item_price < self.avg_item_price:
            raise ValueError("max_item_price cannot be lower than avg_item_price")
        return self


class BatchPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    orders: list[OrderRequest] = Field(min_length=1)


class PredictionResponse(BaseModel):
    request_id: str
    order_id: str | None
    prediction: Literal["late", "on_time"]
    probability: float = Field(ge=0, le=1)
    model_version: str
    validation_status: Literal["passed"] = "passed"


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]
    count: int = Field(ge=1)
    model_version: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_ready: bool
    prediction_store_ready: bool


class ModelInfoResponse(BaseModel):
    name: str
    version: str
    stage: str
    alias: str | None
    source: Literal["mlflow_registry", "local_artifacts"]
    decision_threshold: float | None = Field(default=None, ge=0, le=1)
    transformed_feature_count: int | None = Field(default=None, ge=1)
