from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from olist_mlops.config import load_yaml
from olist_mlops.features import assert_no_leakage

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.data
def test_training_data_schema_ranges_nulls_and_categories() -> None:
    contract = load_yaml(PROJECT_ROOT / "config/feature_contract.yaml")
    train = pd.read_csv(PROJECT_ROOT / "artifacts/03_train.csv.gz", low_memory=False)
    expected_columns = set(
        contract["base_numeric_features"] + contract["base_categorical_features"]
    )
    assert expected_columns.issubset(train.columns)

    for column, rule in contract["numeric_ranges"].items():
        if column not in train:
            continue
        values = pd.to_numeric(train[column], errors="coerce").dropna()
        assert values.between(rule["min"], rule["max"]).all(), column
        missing_rate = train[column].isna().mean()
        maximum = (
            contract["maximum_missing_rate"]["optional"]
            if rule["nullable"]
            else contract["maximum_missing_rate"]["required"]
        )
        assert missing_rate <= maximum, column

    for column, allowed in contract["allowed_categories"].items():
        observed = set(train[column].dropna().astype(str).unique())
        assert observed.issubset(set(allowed)), column


@pytest.mark.data
def test_feature_contract_blocks_labels_future_values_and_identifiers() -> None:
    contract = load_yaml(PROJECT_ROOT / "config/feature_contract.yaml")
    features = (
        contract["base_numeric_features"]
        + contract["base_categorical_features"]
        + contract["engineered_numeric_features"]
    )
    assert_no_leakage(features, contract)
