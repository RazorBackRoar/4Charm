"""4Charm logging setup via razorcore (size-based rotation preserved)."""

from __future__ import annotations

import logging

from razorcore.logging import setup_logging as razorcore_setup_logging


def setup_logging() -> logging.Logger:
    """Setup comprehensive logging with file output and console output."""
    logger = razorcore_setup_logging(
        app_name="4Charm",
        level=logging.DEBUG,
        log_to_file=True,
        log_to_console=True,
        colored_console=True,
        log_filename="4charm.log",
        max_bytes=5 * 1024 * 1024,
        backup_count=3,
        logger_name="4Charm",
        configure_root=True,
    )
    log_path = None
    for handler in logger.handlers:
        base = getattr(handler, "baseFilename", None)
        if base:
            log_path = base
            break
    logger.info("4Charm logging initialized. Log file: %s", log_path)
    return logger
