"""Structured rotating file logging for the Windows collector."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file_path: Path, level_name: str = "INFO") -> None:
    """Configure root logger with rotating file handler and optional console stream."""
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, level_name.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Rotating file handler (10 MB max, up to 5 rotated backup files)
    file_handler = RotatingFileHandler(
        filename=str(log_file_path),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root.addHandler(console_handler)
