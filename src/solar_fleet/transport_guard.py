"""Task-local authority for guarded reads; never store request guards on adapters."""

from contextvars import ContextVar
from typing import Awaitable, Callable, TypeVar

_guards: ContextVar[tuple[Callable[[], None], ...]] = ContextVar("transport_guards", default=())
T = TypeVar("T")


def check_transport_guard() -> None:
    for guard in _guards.get():
        guard()


async def guarded_read(guard: Callable[[], None], read: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
    """Compose nested authority and always restore context, including cancellation."""
    token = _guards.set((*_guards.get(), guard))
    try:
        check_transport_guard()
        result = await read(*args, **kwargs)
        check_transport_guard()
        return result
    finally:
        _guards.reset(token)