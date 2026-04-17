"""Central registry for per-domain `ensure_indexes()` functions.

Each domain registers its own index builder via `register_index_builder`.
`ensure_all_indexes()` is invoked at app startup.
"""

import logging
from typing import Awaitable, Callable, List

logger = logging.getLogger(__name__)

IndexBuilder = Callable[[], Awaitable[None]]
_index_builders: List[IndexBuilder] = []


def register_index_builder(builder: IndexBuilder) -> None:
    _index_builders.append(builder)


async def ensure_all_indexes() -> None:
    for builder in _index_builders:
        try:
            await builder()
        except Exception as exc:
            logger.warning("Index builder %s failed: %s", getattr(builder, "__name__", builder), exc)
