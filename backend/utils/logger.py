"""Structured logging configuration."""

import logging
import sys
from pathlib import Path

import structlog
from structlog.processors import add_log_level, TimeStamper, JSONRenderer

from config import settings


def setup_logging() -> None:
    """Set up structured logging configuration."""

    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Determine log level
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Configure structlog for standard library logging
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        TimeStamper(fmt="iso"),
        JSONRenderer(indent=2 if settings.debug else None),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    log_file = logs_dir / "app.log"

    # Set up handlers
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    handlers.append(file_handler)

    # Configure root logger
    for handler in handlers:
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=processors,
            )
        )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for existing_handler in root_logger.handlers:
        root_logger.removeHandler(existing_handler)
    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(name: str = __name__):
    """Get a structured logger instance."""
    return structlog.get_logger(name)
