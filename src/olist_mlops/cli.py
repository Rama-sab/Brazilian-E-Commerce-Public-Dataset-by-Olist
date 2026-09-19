"""Command-line interface for the same production inference pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from .config import load_settings, load_yaml
from .logging_utils import configure_logging
from .model import load_inference_model
from .schemas import OrderRequest
from .validation import OrderValidator


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Predict Olist delivery lateness")
    parser.add_argument("--config", default="config/settings.yaml")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--json", help="One order as a JSON object")
    source.add_argument("--file", type=Path, help="JSON file with one order or a list")
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = load_settings(args.config)
    configure_logging(settings)
    raw = json.loads(args.json) if args.json else json.loads(args.file.read_text("utf-8"))
    payloads = raw if isinstance(raw, list) else [raw]
    orders = [OrderRequest.model_validate(payload) for payload in payloads]
    frame = pd.DataFrame([order.model_dump(mode="python") for order in orders])
    contract = load_yaml(settings.path("paths.feature_contract"))
    OrderValidator(contract).validate(frame)
    model = load_inference_model(settings)
    outputs = model.predict_frame(frame).to_dict(orient="records")
    for order, output in zip(orders, outputs, strict=True):
        output["order_id"] = order.order_id
        output["model_version"] = model.metadata.version
    sys.stdout.write(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
