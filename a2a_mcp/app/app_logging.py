"""
App logging module.
"""
import logging
from typing import Optional

# Global context for tracing (in a real app, use ContextVars for thread safety)
_current_trace_id: Optional[str] = None

class ContextFormatter(logging.Formatter):
    """Custom formatter to inject trace_id into log records."""
    def format(self, record):
        record.trace_id = getattr(record, "trace_id", _current_trace_id or "no-trace")
        return super().format(record)

def setup_logging(level=logging.INFO):
    """Configures centralized logging with trace support."""
    log_format = "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"
    formatter = ContextFormatter(log_format)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Clear existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)

def set_trace_id(trace_id: str):
    """Sets the global trace id."""
    global _current_trace_id  # pylint: disable=global-statement
    _current_trace_id = trace_id

setup_logging()
logger = logging.getLogger("middleware")
