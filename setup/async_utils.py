from __future__ import annotations

import asyncio
import inspect
from concurrent.futures import Future
from typing import Awaitable, TypeVar

T = TypeVar("T")


def submit_coroutine(loop: asyncio.AbstractEventLoop, coroutine: Awaitable[T]) -> Future[T]:
    """Submit an already-created coroutine to a running background event loop."""
    if not inspect.isawaitable(coroutine):
        raise TypeError("expected a coroutine; call the async method with parentheses")
    return asyncio.run_coroutine_threadsafe(coroutine, loop)
