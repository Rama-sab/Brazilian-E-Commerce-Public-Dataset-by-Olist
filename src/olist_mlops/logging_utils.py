"""Application logging configuration."""

from __future__ import annotations

import logging
import logging.config

from .config import Settings


def configure_logging(settings: Settings) -> None:
    log_path = settings.path("paths.log_file")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = str(settings.get("logging.level", "INFO")).upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": settings.get("logging.format"),
                    "datefmt": settings.get("logging.date_format"),
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": level,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(log_path),
                    "formatter": "standard",
                    "level": level,
                    "maxBytes": int(settings.get("logging.max_bytes")),
                    "backupCount": int(settings.get("logging.backup_count")),
                    "encoding": "utf-8",
                },
            },
            "root": {"handlers": ["console", "file"], "level": level},
        }
    )
