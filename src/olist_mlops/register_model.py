"""Register the frozen Task 2 model and fitted preprocessor in MLflow."""

from __future__ import annotations

import json
import logging
import sys

import mlflow
import pandas as pd

from .config import load_settings, load_yaml
from .model import OlistPyFuncModel

LOGGER = logging.getLogger(__name__)


def register(config_path: str = "config/settings.yaml") -> str:
    settings = load_settings(config_path)
    tracking_uri = str(settings.get("model.tracking_uri"))
    model_name = str(settings.get("model.name"))
    alias = str(settings.get("model.alias"))
    stage = str(settings.get("model.expected_stage"))
    contract = load_yaml(settings.path("paths.feature_contract"))
    results_path = settings.project_root / "models/seed/06_results_summary.json"
    feature_list_path = settings.project_root / "models/seed/05_feature_list.json"
    example_path = settings.project_root / "models/seed/example_order.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    feature_list = json.loads(feature_list_path.read_text(encoding="utf-8"))
    input_example = pd.DataFrame([json.loads(example_path.read_text(encoding="utf-8"))])

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("olist-late-delivery-inference")
    with mlflow.start_run(run_name="register-frozen-task2-model") as run:
        mlflow.log_params(
            {
                "selected_C": results["selected_C"],
                "decision_threshold": results["selected_threshold"],
                "positive_class": "late",
                "training_pipeline": "notebooks/05 and 06",
                "refit_during_registration": False,
            }
        )
        for split in ("validation", "test"):
            metrics = results[split]["logistic_regression"]
            for metric, value in metrics.items():
                mlflow.log_metric(f"{split}_{metric}", float(value))
        mlflow.log_artifact(str(results_path), artifact_path="evidence")
        mlflow.log_artifact(str(feature_list_path), artifact_path="evidence")
        logged = mlflow.pyfunc.log_model(
            name="inference_model",
            python_model=OlistPyFuncModel(contract),
            artifacts={
                "preprocessor": str(settings.path("model.local_preprocessor_path")),
                "model_bundle": str(settings.path("model.local_bundle_path")),
            },
            input_example=input_example,
            # The Pydantic and GX contracts validate inputs at the API boundary.
            # Disabling MLflow's inferred signature preserves nullable integer
            # columns and Python datetime values after Pydantic serialization.
            signature=False,
            pip_requirements=[
                "joblib==1.5.3",
                "mlflow==3.15.0",
                "numpy==2.3.5",
                "pandas==2.3.2",
                "scikit-learn==1.9.0",
                "scipy==1.18.1",
            ],
        )
        version = mlflow.register_model(
            model_uri=logged.model_uri,
            name=model_name,
            await_registration_for=300,
            tags={"source_run_id": run.info.run_id},
        )

    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    tags = {
        "stage": stage,
        "decision_threshold": str(results["selected_threshold"]),
        "transformed_feature_count": str(len(feature_list)),
        "preprocessor_fitted": "true",
        "training_performed": "false",
    }
    for key, value in tags.items():
        client.set_model_version_tag(model_name, version.version, key, value)
    client.set_registered_model_alias(model_name, alias, version.version)
    LOGGER.info(
        "Registered model name=%s version=%s alias=%s stage=%s",
        model_name,
        version.version,
        alias,
        stage,
    )
    return str(version.version)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/settings.yaml"
    register(config_path)


if __name__ == "__main__":
    main()
