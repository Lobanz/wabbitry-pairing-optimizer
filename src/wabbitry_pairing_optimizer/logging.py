"""Run logging to a file in the output dir (design §9 / operator request).

Operator policy: logging goes to a FILE (in the output dir), NOT stdout, so the
CLI emission layer (`--output json|text`) stays clean and machine-readable. The
config selects level and format (`[output].log_format` = "json" JSON-lines or
"text" single-line).

Single concern: log configuration (return a stdlib ``logging.Logger``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from wabbitry_pairing_optimizer.config import OutputConfig

__all__ = ["setup_logging", "get_logger"]

#: The logger used across the run; configured once by setup_logging.
_RUN_LOGGER = "wabbitry"


class _JsonFormatter(logging.Formatter):
    """Emit each record as one JSON line (agent-friendly, grep/parse-able)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(output_cfg: OutputConfig, output_dir: str) -> logging.Logger:
    """Configure the run logger to write into ``output_dir``.

    Args:
        output_cfg: The `[output]` config (filename/level/format).
        output_dir: Resolved output directory (CLI override may differ from
            config default).

    Returns:
        The configured run logger.
    """
    logger = logging.getLogger(_RUN_LOGGER)
    logger.setLevel(getattr(logging, output_cfg.log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    log_path = Path(output_dir) / output_cfg.log_filename
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    if output_cfg.log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    """Return the run logger (configure by setup_logging first)."""
    return logging.getLogger(_RUN_LOGGER)
