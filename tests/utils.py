# ---------------------------------------------------------------------
# Gufo Blob: Test utilities
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from __future__ import annotations

from collections.abc import AsyncIterable
from typing import TypeVar

T = TypeVar("T")


async def sort_async_iterable(seq: AsyncIterable[T]) -> list[T]:
    """
    Collect async iterable and sort result.

    Args:
        seq: Async iterable to collect.

    Returns:
        Sorted result as list.
    """
    r: list[T] = []
    async for x in seq:
        r.append(x)
    return sorted(r)
