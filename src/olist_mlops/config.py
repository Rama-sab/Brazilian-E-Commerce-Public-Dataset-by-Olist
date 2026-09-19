"""Configuration loading with environment-variable interpolation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return default
        raise KeyError(f"Required environment variable is not set: {name}")

    expanded = _ENV_PATTERN.sub(replace, value)
    lowered = expanded.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if re.fullmatch(r"-?\d+", expanded):
        return int(expanded)
    if re.fullmatch(r"-?(?:\d+\.\d*|\d*\.\d+)", expanded):
        return float(expanded)
    return expanded


@dataclass(frozen=True)
class Settings:
    """Resolved application settings and project-relative path helpers."""

    values: dict[str, Any]
    project_root: Path

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.values
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def path(self, dotted_key: str) -> Path:
        raw = self.get(dotted_key)
        if not raw:
            raise KeyError(f"Missing configured path: {dotted_key}")
        path = Path(str(raw))
        return path if path.is_absolute() else (self.project_root / path).resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return _expand_env(content)


def load_settings(config_path: str | Path | None = None) -> Settings:
    configured = config_path or os.getenv("OLIST_CONFIG_PATH", "config/settings.yaml")
    path = Path(configured).resolve()
    values = load_yaml(path)
    project_root = path.parent.parent
    required = [
        "service.name",
        "model.loader",
        "paths.feature_contract",
        "validation.failure_policy",
    ]
    settings = Settings(values=values, project_root=project_root)
    missing = [key for key in required if settings.get(key) is None]
    if missing:
        raise ValueError(f"Missing required configuration values: {missing}")
    return settings
