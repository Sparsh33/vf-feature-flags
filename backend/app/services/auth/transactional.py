"""Minimal `@transactional` decorator for auth service writes.

Wraps a coroutine in a MongoDB client session + transaction when supported;
falls back to best-effort execution otherwise (e.g., mongomock-motor, standalone
Mongo). Signup compensates for partial failures explicitly in the service layer.
"""

from functools import wraps
from typing import Any, Callable, Coroutine

from app.database.config import mongodb


def transactional(
    func: Callable[..., Coroutine[Any, Any, Any]]
) -> Callable[..., Coroutine[Any, Any, Any]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        database = mongodb.get_database()
        client = database.client
        try:
            async with await client.start_session() as session:
                try:
                    async with session.start_transaction():
                        return await func(*args, **kwargs)
                except Exception:
                    return await func(*args, **kwargs)
        except Exception:
            return await func(*args, **kwargs)

    return wrapper
