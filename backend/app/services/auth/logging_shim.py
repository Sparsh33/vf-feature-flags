"""Thin wrapper around `app.common.logging_helpers` that swallows helper errors.

The scaffolded `_enrich` helper places `"message"` into the logging `extra` dict,
which collides with Python 3.12's `LogRecord` reserved attribute and raises
`KeyError`. We cannot edit `app/common/` from this domain, so auth wraps the
helpers defensively. Logging must never crash a request path.
"""

from app.common import logging_helpers as _helpers
from app.common.logging_helpers import LoggingData


def log_info(data: LoggingData) -> None:
    try:
        _helpers.log_info(data)
    except Exception:
        pass


def log_warning(data: LoggingData) -> None:
    try:
        _helpers.log_warning(data)
    except Exception:
        pass


def log_error(data: LoggingData) -> None:
    try:
        _helpers.log_error(data)
    except Exception:
        pass


def log_debug(data: LoggingData) -> None:
    try:
        _helpers.log_debug(data)
    except Exception:
        pass
