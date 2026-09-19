from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from olist_mlops.config import load_yaml
from olist_mlops.features import assert_no_leakage, build_feature_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_feature_builder_matches_notebook_date_logic() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "models/seed/example_order.json").read_text(encoding="utf-8")
    )
    contract = load_yaml(PROJECT_ROOT / "config/feature_contract.yaml")
    features = build_feature_frame(pd.DataFrame([payload]), contract)

    assert features.loc[0, "purchase_year"] == 2018
    assert features.loc[0, "purchase_month"] == 6
    assert features.loc[0, "purchase_dayofweek"] == 3
    assert features.loc[0, "purchase_hour"] == 8
    assert features.loc[0, "purchase_is_weekend"] == 0
    assert features.loc[0, "purchase_is_fixed_holiday"] == 0
    assert features.loc[0, "estimated_delivery_lead_days"] == pytest.approx(12.6381134259)
    assert_no_leakage(features.columns.tolist(), contract)


def test_optional_numeric_values_remain_missing_for_fitted_imputer() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "models/seed/example_order.json").read_text(encoding="utf-8")
    )
    payload["product_weight_g_mean"] = None
    contract = load_yaml(PROJECT_ROOT / "config/feature_contract.yaml")
    features = build_feature_frame(pd.DataFrame([payload]), contract)
    assert pd.isna(features.loc[0, "product_weight_g_mean"])
