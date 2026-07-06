# ---------------------------------------------------------------------
# Gufo Blob: Async wrapper for sync implementation
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------


# Python modules
from __future__ import annotations

from asyncio import Lock, to_thread
from collections.abc import AsyncIterator, Iterable, Iterator
from typing import Any, Generic, TypeVar

# Gufo Blob modules
from ..sync.base import BlobBase as SyncBase
from .base import BlobBase

T = TypeVar("T", bound=SyncBase)


class AsyncWrapper(BlobBase, Generic[T]):
    inner: type[T]  # must be defined in subclasses

    def __init__(self, sync: T) -> None:
        self._sync = sync

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        return cls.inner.parse_url(url)

    async def put(self, key: str, data: bytes) -> None:
        def inner() -> None:
            self._sync.put(key, data)

        await to_thread(inner)

    async def get(self, key: str) -> bytes:
        def inner() -> bytes:
            return self._sync.get(key)

        return await to_thread(inner)

    async def delete(self, key: str) -> None:
        def inner() -> None:
            self._sync.delete(key)

        await to_thread(inner)

    async def exists(self, key: str) -> bool:
        def inner() -> bool:
            return self._sync.exists(key)

        return await to_thread(inner)

    async def scan(self, prefix: str) -> AsyncIterator[str]:
        def inner() -> list[str]:
            return list(self._sync.scan(prefix))

        for x in await to_thread(inner):
            yield x


TI = TypeVar("TI")


class AsyncIterWrapper(Generic[TI]):
    def __init__(self, inner: Iterable[TI], lock: Lock) -> None:
        self._inner: Iterable[TI] = inner
        self._snapshot: Iterator[TI] | None = None
        self._lock = lock

    def __aiter__(self) -> AsyncIterWrapper[TI]:
        return self

    async def __anext__(self) -> TI:
        if self._snapshot is None:
            async with self._lock:
                self._snapshot = iter(list(self._inner))
        try:
            return next(self._snapshot)
        except StopIteration as e:
            raise StopAsyncIteration from e
