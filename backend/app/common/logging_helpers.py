"""Structured logging helpers. Domains must use these, never `logging` directly."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.middleware.request_context import RequestContextManager

_logger = logging.getLogger("vf_ff")


@dataclass
class LoggingData:
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    error: Optional[BaseException] = None


def _enrich(data: LoggingData) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "message": data.message,
        "request_id": RequestContextManager.get_request_id(),
        "user_id": RequestContextManager.get_user_id(),
        "client_id": RequestContextManager.get_client_id(),
    }
    payload.update(data.context)
    return payload


def log_info(data: LoggingData) -> None:
    _logger.info(data.message, extra=_enrich(data))


def log_warning(data: LoggingData) -> None:
    _logger.warning(data.message, extra=_enrich(data))


def log_error(data: LoggingData) -> None:
    extra = _enrich(data)
    if data.error is not None:
        _logger.error(data.message, extra=extra, exc_info=data.error)
    else:
        _logger.error(data.message, extra=extra)


def log_debug(data: LoggingData) -> None:
    _logger.debug(data.message, extra=_enrich(data))
