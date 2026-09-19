from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from olist_mlops.config import load_yaml
from olist_mlops.model import NativeInferenceModel
from olist_mlops.schemas import OrderRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _model() -> NativeInferenceModel:
    return NativeInferenceModel(
        preprocessor_path=PROJECT_ROOT / "models/seed/05_preprocessor.joblib",
        model_bundle_path=PROJECT_ROOT / "models/seed/06_final_model.joblib",
        contract=load_yaml(PROJECT_ROOT / "config/feature_contract.yaml"),
        name="olist-late-delivery",
        version="test-v1",
    )


def _raw_inference_rows(count: int = 5) -> pd.DataFrame:
    source = pd.read_csv(PROJECT_ROOT / "artifacts/03_test.csv.gz", nrows=count)
    columns = list(OrderRequest.model_fields)
    result = source.reindex(columns=columns).copy()
    return result.astype(object).where(result.notna(), None)


def test_saved_model_predicts_expected_shape_and_probability_bounds() -> None:
    outputs = _model().predict_frame(_raw_inference_rows())
    assert outputs.shape == (5, 2)
    assert outputs["prediction"].isin(["late", "on_time"]).all()
    assert outputs["probability"].between(0, 1).all()


def test_module_pipeline_exactly_matches_notebook_predictions() -> None:
    raw = _raw_inference_rows()
    outputs = _model().predict_frame(raw)
    expected_all = pd.read_csv(PROJECT_ROOT / "artifacts/06_test_predictions.csv.gz")
    expected = (
        expected_all.set_index("order_id")
        .loc[raw["order_id"], "predicted_late_probability"]
        .to_numpy()
    )
    np.testing.assert_allclose(outputs["probability"].to_numpy(), expected, rtol=0, atol=1e-14)


def test_inference_does_not_modify_fitted_artifacts() -> None:
    paths = [
        PROJECT_ROOT / "models/seed/05_preprocessor.joblib",
        PROJECT_ROOT / "models/seed/06_final_model.joblib",
    ]
    before = [path.read_bytes() for path in paths]
    _model().predict_frame(_raw_inference_rows(1))
    after = [path.read_bytes() for path in paths]
    assert after == before
