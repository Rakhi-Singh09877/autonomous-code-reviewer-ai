import os
import sys
import json
import logging
import contextvars
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Global context variable for tracking unique request IDs across threads/tasks
request_id_ctx_var = contextvars.ContextVar("request_id", default="")

class RequestIDFilter(logging.Filter):
    """
    Logging Filter injecting request_id from context variables into standard LogRecord logs.
    """
    def filter(self, record):
        record.request_id = request_id_ctx_var.get()
        return True

class PlainFormatter(logging.Formatter):
    """
    Standard text formatter structuring log messages as plain text templates.
    """
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def format(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx_var.get()
        return super().format(record)

class JsonFormatter(logging.Formatter):
    """
    Structured logging formatter outputting log entries as parseable JSON strings.
    """
    def format(self, record):
        request_id = getattr(record, "request_id", "") or request_id_ctx_var.get()
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging() -> None:
    """
    Configures the root logging logger with file and console handlers and dynamic formatters.
    """
    log_level_str = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_format = settings.LOG_FORMAT.lower()
    log_file_path = settings.LOG_FILE_PATH

    # Choose the abstract formatter implementation dynamically
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = PlainFormatter()

    # Ensure log destination directories exist before registering handler
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    handlers = []

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    handlers.append(console_handler)

    # 2. Rotating File Handler
    if log_file_path:
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10 MB per file
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(RequestIDFilter())
            handlers.append(file_handler)
        except Exception as e:
            # Fallback to sys.stderr if directory is read-only
            print(f"Failed to initialize file logger: {e}", file=sys.stderr)

    # 3. Apply settings to the Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clean existing handlers to avoid duplicates
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    for handler in handlers:
        root_logger.addHandler(handler)

# Initialize standard logger name
logger = logging.getLogger("autonomous_code_reviewer")
