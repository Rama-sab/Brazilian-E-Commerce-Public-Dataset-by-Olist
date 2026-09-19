"""Artifact-backed and MLflow Registry-backed inference models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import joblib
import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
from scipy import sparse

from .config import Settings, load_yaml
from .features import assert_no_leakage, build_feature_frame


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str
    stage: str
    alias: str | None
    source: str
    decision_threshold: float | None
    transformed_feature_count: int | None


class InferenceModel(Protocol):
    metadata: ModelMetadata

    def predict_frame(self, raw_frame: pd.DataFrame) -> pd.DataFrame: ...


class NativeInferenceModel:
    """Use the exact fitted Notebook 05 and 06 objects without refitting."""

    def __init__(
        self,
        *,
        preprocessor_path: Path,
        model_bundle_path: Path,
        contract: dict[str, Any],
        name: str,
        version: str,
        stage: str = "Local verification",
    ) -> None:
        self.preprocessor = joblib.load(preprocessor_path)
        self.bundle = joblib.load(model_bundle_path)
        self.contract = contract
        self.classifier = self.bundle["classifier"]
        self.threshold = float(self.bundle["decision_threshold"])
        artifact_features = list(self.bundle["feature_names"])
        fitted_features = self.preprocessor.get_feature_names_out().tolist()
        if artifact_features != fitted_features:
            raise ValueError("Model and preprocessor transformed feature lists do not match")
        if self.classifier.n_features_in_ != len(artifact_features):
            raise ValueError("Classifier feature count does not match its saved feature list")
        self.metadata = ModelMetadata(
            name=name,
            version=version,
            stage=stage,
            alias=None,
            source="local_artifacts",
            decision_threshold=self.threshold,
            transformed_feature_count=len(artifact_features),
        )

    def predict_frame(self, raw_frame: pd.DataFrame) -> pd.DataFrame:
        features = build_feature_frame(raw_frame, self.contract)
        assert_no_leakage(features.columns.tolist(), self.contract)
        transformed = sparse.csr_matrix(self.preprocessor.transform(features))
        probabilities = self.classifier.predict_proba(transformed)[:, 1]
        predictions = np.where(probabilities >= self.threshold, "late", "on_time")
        return pd.DataFrame(
            {
                "prediction": predictions,
                "probability": probabilities.astype(float),
            },
            index=raw_frame.index,
        )


class RegistryInferenceModel:
    """Load the deployable model by MLflow Registry alias."""

    def __init__(self, settings: Settings) -> None:
        name = str(settings.get("model.name"))
        alias = str(settings.get("model.alias"))
        tracking_uri = str(settings.get("model.tracking_uri"))
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.MlflowClient(tracking_uri=tracking_uri)
        version = client.get_model_version_by_alias(name, alias)
        self.model = mlflow.pyfunc.load_model(f"models:/{name}@{alias}")
        self.metadata = ModelMetadata(
            name=name,
            version=str(version.version),
            stage=version.tags.get("stage", settings.get("model.expected_stage")),
            alias=alias,
            source="mlflow_registry",
            decision_threshold=(
                float(version.tags["decision_threshold"])
                if "decision_threshold" in version.tags
                else None
            ),
            transformed_feature_count=(
                int(version.tags["transformed_feature_count"])
                if "transformed_feature_count" in version.tags
                else None
            ),
        )

    def predict_frame(self, raw_frame: pd.DataFrame) -> pd.DataFrame:
        result = self.model.predict(raw_frame)
        if not isinstance(result, pd.DataFrame):
            result = pd.DataFrame(result)
        expected = {"prediction", "probability"}
        missing = sorted(expected.difference(result.columns))
        if missing:
            raise ValueError(f"Registered model output is missing columns: {missing}")
        return result.loc[:, ["prediction", "probability"]]


class OlistPyFuncModel(mlflow.pyfunc.PythonModel):
    """Portable MLflow model that packages preprocessing and classification."""

    def __init__(self, contract: dict[str, Any]) -> None:
        self.contract = contract

    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        self.preprocessor = joblib.load(context.artifacts["preprocessor"])
        self.bundle = joblib.load(context.artifacts["model_bundle"])
        self.classifier = self.bundle["classifier"]
        self.threshold = float(self.bundle["decision_threshold"])

    def predict(
        self,
        context: mlflow.pyfunc.PythonModelContext,
        model_input: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        del context, params
        features = build_feature_frame(model_input, self.contract)
        assert_no_leakage(features.columns.tolist(), self.contract)
        matrix = sparse.csr_matrix(self.preprocessor.transform(features))
        probabilities = self.classifier.predict_proba(matrix)[:, 1]
        return pd.DataFrame(
            {
                "prediction": np.where(probabilities >= self.threshold, "late", "on_time"),
                "probability": probabilities.astype(float),
            }
        )


def load_inference_model(settings: Settings) -> InferenceModel:
    loader = str(settings.get("model.loader")).lower()
    if loader == "registry":
        return RegistryInferenceModel(settings)
    if loader == "local":
        contract = load_yaml(settings.path("paths.feature_contract"))
        return NativeInferenceModel(
            preprocessor_path=settings.path("model.local_preprocessor_path"),
            model_bundle_path=settings.path("model.local_bundle_path"),
            contract=contract,
            name=str(settings.get("model.name")),
            version=str(settings.get("model.local_version")),
        )
    raise ValueError(f"Unsupported model.loader value: {loader}")
