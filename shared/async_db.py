"""Run sync SQLite/repo calls off the event loop."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def run(func: Callable[..., T], *args, **kwargs) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)
