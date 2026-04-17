"""Celery task autodiscovery hub.

Each domain's tasks module is imported lazily with try/except so the
worker can boot even while some domains are still unimplemented.
"""

import logging

_logger = logging.getLogger(__name__)

_DOMAIN_TASK_MODULES = [
    "app.services.audit.tasks",
    "app.services.analytics.tasks",
]

for _module_path in _DOMAIN_TASK_MODULES:
    try:
        __import__(_module_path)
    except ImportError as _exc:
        _logger.warning("Task module %s not available: %s", _module_path, _exc)
