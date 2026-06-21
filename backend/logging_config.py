"""Structured JSON logging configuration for ZFP Advisor.

Every log line is a JSON object — Azure Monitor / Log Analytics picks these
up automatically and makes them queryable.

Usage:
    from backend.logging_config import get_logger
    logger = get_logger("advisor.powerbi")
    logger.info("dax_executed", extra={"extra": {"rows": 5, "ms": 120}})
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, UTC
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Allow callers to attach structured fields via extra={"extra": {...}}
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _configure_root() -> None:
    root = logging.getLogger()
    if root.handlers:
        return  # already configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


_configure_root()


def get_logger(name: str) -> logging.Logger:
    """Return a structured logger for the given name."""
    return logging.getLogger(name)
