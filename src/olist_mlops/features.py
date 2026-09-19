"""Prediction-time feature construction copied from Notebook 05."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def build_feature_frame(frame: pd.DataFrame, contract: dict[str, Any]) -> pd.DataFrame:
    """Build raw model features without fitting any transformer."""
    required_dates = {"order_purchase_timestamp", "order_estimated_delivery_date"}
    missing_dates = sorted(required_dates.difference(frame.columns))
    if missing_dates:
        raise ValueError(f"Missing date columns needed for feature engineering: {missing_dates}")

    work = frame.copy()
    for column in required_dates:
        work[column] = pd.to_datetime(work[column], errors="coerce")
    if work[list(required_dates)].isna().any().any():
        raise ValueError("Purchase and estimated-delivery timestamps must be valid dates")

    features = pd.DataFrame(index=work.index)
    for column in contract["base_numeric_features"]:
        source = work[column] if column in work else pd.Series(np.nan, index=work.index)
        features[column] = pd.to_numeric(source, errors="coerce")
    for column in contract["base_categorical_features"]:
        source = work[column] if column in work else pd.Series(np.nan, index=work.index)
        features[column] = source.astype(object).where(source.notna(), np.nan)

    purchase = work["order_purchase_timestamp"]
    estimated = work["order_estimated_delivery_date"]
    features["estimated_delivery_lead_days"] = (estimated - purchase).dt.total_seconds() / 86400
    features["purchase_year"] = purchase.dt.year
    features["purchase_month"] = purchase.dt.month
    features["purchase_dayofweek"] = purchase.dt.dayofweek
    features["purchase_hour"] = purchase.dt.hour
    features["purchase_is_weekend"] = purchase.dt.dayofweek.ge(5).astype("int8")
    fixed_holidays = {tuple(value) for value in contract["fixed_holidays"]}
    features["purchase_is_fixed_holiday"] = [
        int((month, day) in fixed_holidays)
        for month, day in zip(purchase.dt.month, purchase.dt.day, strict=True)
    ]

    expected = (
        contract["base_numeric_features"]
        + contract["base_categorical_features"]
        + contract["engineered_numeric_features"]
    )
    return features.reindex(columns=expected)


def assert_no_leakage(feature_columns: list[str], contract: dict[str, Any]) -> None:
    forbidden = set(
        contract["leakage_columns"] + contract["identifier_or_high_cardinality_columns"]
    )
    leaked = sorted(forbidden.intersection(feature_columns))
    if leaked:
        raise ValueError(f"Leakage or identifier columns reached inference features: {leaked}")
