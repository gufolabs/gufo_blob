# ---------------------------------------------------------------------
# Gufo Blob: Async interface
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""Asynchronous BlobBase definition."""

# Python modules
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any

# Third-party modules
from gufo.loader import Loader

# Gufo Blob modules
from ..error import BlobError


class BlobBase(ABC):
    """
    Gufo Blob: async key-value object store abstraction.

    This module defines a minimal interface for working with binary
    objects stored in a backend-agnostic keyspace.

    The model is intentionally simple:

        key (str) -> value (bytes)

    It supports multiple backends via a URL-based loader mechanism.

    This is not a filesystem abstraction:
    there are no directories, inodes, or POSIX semantics.

    Only a flat keyspace with optional prefix scanning.
    """

    name: str

    @classmethod
    @abstractmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """
        Parse URL and extract parameters for constructor.

        Args:
            url: URL to parse.

        Returns:
            `**kwargs` for constructor.

        Raises:
            BlobError: on error.
        """

    @classmethod
    def from_url(cls, url: str) -> BlobBase:
        """
        Create a blob backend instance from a URL.

        The URL defines the storage backend and its configuration.
        The schema part selects the backend implementation.

        Examples:
            /var/data
            memory://
            s3://bucket/prefix

        Args:
            url: Backend-specific URL.

        Returns:
            Initialized BlobBase instance.

        Raises:
            BlobError: If the schema is unsupported or initialization fails.
        """
        kwargs = cls.parse_url(url)
        return cls(**kwargs)

    async def open(self) -> None:  # noqa: B027
        """Perform connection routines when necessary."""

    async def close(self) -> None:  # noqa: B027
        """Perform cleanup routines when necessary."""

    async def __aenter__(self) -> BlobBase:
        """Async context manager enter."""
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Asynchronous context manager exit."""
        await self.close()
        return None

    @abstractmethod
    async def put(self, key: str, data: bytes) -> None:
        """
        Store binary data under the given key.

        If the key already exists, its value is overwritten.

        Args:
            key: Object key.
            data: Binary payload.

        Raises:
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """
        Retrieve data by key.

        Args:
            key: Object key.

        Raises:
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the blob store.

        Args:
            key: Object key.

        Returns:
            True if the key exists, False otherwise.

        Raises:
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    def scan(self, prefix: str) -> AsyncIterator[str]:
        """
        Iterate all keys within prefix.

        Args:
            prefix: Prefix to scan.

        Returns:
            Yields matched keys.

        Raises:
            BlobError: On backend or I/O failure.
        """


loader = Loader[type[BlobBase]](base="gufo.blob.aio", exclude=["base"])


def open_blob(url: str) -> BlobBase:
    """
    Open a blob store instance from URL.

    This is the main entry point for creating a blob backend
    based on a URL schema.

    The schema part of the URL selects the backend implementation,
    while the rest of the URL is backend-specific configuration.

    Examples:
        /var/data
        memory:///
        s3://bucket/prefix

    Args:
        url: Storage backend URL.

    Returns:
        Initialized blob store instance.

    Raises:
        BlobError: If the schema is not supported or backend
            initialization fails.
    """
    schema = url.split(":", 1)[0] if ":" in url else "file"
    try:
        return loader[schema].from_url(url)
    except KeyError as e:
        msg = f"invalid schema: {schema}"
        raise BlobError(msg) from e
