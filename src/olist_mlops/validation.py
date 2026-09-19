"""Great Expectations validation for incoming inference records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import great_expectations as gx
import pandas as pd

from .features import build_feature_frame


@dataclass(frozen=True)
class ValidationReport:
    success: bool
    failures: list[dict[str, Any]]


class DataValidationError(ValueError):
    def __init__(self, failures: list[dict[str, Any]]) -> None:
        super().__init__("Incoming order failed the Great Expectations contract")
        self.failures = failures


class OrderValidator:
    """Validate schema semantics, ranges, categories, and missing values with GX."""

    def __init__(self, contract: dict[str, Any]) -> None:
        self.contract = contract
        self.context = gx.get_context(mode="ephemeral")
        suffix = uuid4().hex
        source = self.context.data_sources.add_pandas(name=f"inference_{suffix}")
        asset = source.add_dataframe_asset(name=f"orders_{suffix}")
        self.batch_definition = asset.add_batch_definition_whole_dataframe(
            name=f"whole_frame_{suffix}"
        )

    def _expectations(self) -> list[Any]:
        expectations: list[Any] = []
        required = set(self.contract["required_columns"])
        for column in self.contract["base_numeric_features"]:
            rule = self.contract["numeric_ranges"][column]
            expectations.append(
                gx.expectations.ExpectColumnValuesToBeBetween(
                    column=column,
                    min_value=rule["min"],
                    max_value=rule["max"],
                    mostly=1.0,
                )
            )
            if column in required or not rule["nullable"]:
                expectations.append(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
        lead_rule = self.contract["numeric_ranges"]["estimated_delivery_lead_days"]
        expectations.extend(
            [
                gx.expectations.ExpectColumnValuesToBeBetween(
                    column="estimated_delivery_lead_days",
                    min_value=lead_rule["min"],
                    max_value=lead_rule["max"],
                ),
                gx.expectations.ExpectColumnValuesToNotBeNull(
                    column="estimated_delivery_lead_days"
                ),
            ]
        )
        for column, allowed in self.contract["allowed_categories"].items():
            expectations.extend(
                [
                    gx.expectations.ExpectColumnValuesToNotBeNull(column=column),
                    gx.expectations.ExpectColumnValuesToBeInSet(column=column, value_set=allowed),
                ]
            )
        return expectations

    def validate(
        self, raw_frame: pd.DataFrame, *, raise_on_failure: bool = True
    ) -> ValidationReport:
        feature_frame = build_feature_frame(raw_frame, self.contract)
        batch = self.batch_definition.get_batch(batch_parameters={"dataframe": feature_frame})
        failures: list[dict[str, Any]] = []
        for expectation in self._expectations():
            result = batch.validate(expectation)
            if not result.success:
                details = dict(result.result or {})
                failures.append(
                    {
                        "expectation": expectation.__class__.__name__,
                        "column": getattr(expectation, "column", None),
                        "unexpected_count": details.get("unexpected_count"),
                        "unexpected_values": details.get("partial_unexpected_list", []),
                    }
                )
        report = ValidationReport(success=not failures, failures=failures)
        if failures and raise_on_failure:
            raise DataValidationError(failures)
        return report
