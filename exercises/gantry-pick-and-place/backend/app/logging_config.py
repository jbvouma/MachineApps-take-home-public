"""Structured logging setup with an env-configurable level (LOG_LEVEL, default INFO)."""

from __future__ import annotations

import logging

from app.config import SETTINGS

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once. Idempotent across calls."""
    resolved = (level or SETTINGS.log_level).upper()
    logging.basicConfig(level=resolved, format=_LOG_FORMAT, force=True)
    logging.getLogger(__name__).debug("Logging configured at level %s", resolved)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
