import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Setup comprehensive logging with file output and console output."""
    # Create log directory in user's home
    log_dir = Path.home() / ".4charm" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "4charm.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")

    # Create handlers
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

    logger = logging.getLogger("4Charm")
    logger.info(f"4Charm logging initialized. Log file: {log_file}")

    return logger
