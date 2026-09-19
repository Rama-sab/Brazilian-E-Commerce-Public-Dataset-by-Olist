from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from olist_mlops.config import load_yaml
from olist_mlops.validation import DataValidationError, OrderValidator

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def validator() -> OrderValidator:
    contract = load_yaml(PROJECT_ROOT / "config/feature_contract.yaml")
    return OrderValidator(contract)


def payload() -> dict:
    return json.loads((PROJECT_ROOT / "models/seed/example_order.json").read_text(encoding="utf-8"))


def test_great_expectations_accepts_valid_order(validator: OrderValidator) -> None:
    report = validator.validate(pd.DataFrame([payload()]))
    assert report.success
    assert report.failures == []


def test_great_expectations_rejects_unknown_category(validator: OrderValidator) -> None:
    invalid = payload()
    invalid["payment_type_mode"] = "cryptocurrency"
    with pytest.raises(DataValidationError) as error:
        validator.validate(pd.DataFrame([invalid]))
    assert any(failure["column"] == "payment_type_mode" for failure in error.value.failures)


def test_great_expectations_rejects_out_of_range_value(
    validator: OrderValidator,
) -> None:
    invalid = payload()
    invalid["total_price"] = 1_000_000
    with pytest.raises(DataValidationError) as error:
        validator.validate(pd.DataFrame([invalid]))
    assert any(failure["column"] == "total_price" for failure in error.value.failures)


def test_fitted_imputer_handles_allowed_missing_value(validator: OrderValidator) -> None:
    valid = payload()
    valid["customer_seller_distance_km"] = None
    assert validator.validate(pd.DataFrame([valid])).success
