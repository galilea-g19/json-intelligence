import logging
import sys
from pathlib import Path

# Create the logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

def setup_logging():
    """Configure the application's logging system."""

    root_logger = logging.getLogger()
    # Avoid duplicating handlers if setup_logging() is called more than once
    # (common with uvicorn --reload), which would repeat every log line.
    if root_logger.handlers:
        return

    # Log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    # File handler (all levels)
    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)

    # Configure the root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noisy logs from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.WARNING)