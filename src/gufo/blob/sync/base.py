# ---------------------------------------------------------------------
# Gufo Blob: Sync interface
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""Synchronous BlobBase definition."""

# Python modules
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from types import TracebackType
from typing import Any

# Third-party modules
from gufo.loader import Loader

# Gufo Blob modules
from ..error import BlobError


class BlobBase(ABC):
    """
    Gufo Blob: synchronous key-value object store abstraction.

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

    def open(self) -> None:  # noqa: B027
        """Perform connection routines when necessary."""

    def close(self) -> None:  # noqa: B027
        """Perform cleanup routines when necessary."""

    def __enter__(self) -> BlobBase:
        """Context manager enter."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        """Context manager exit."""
        self.close()
        return None

    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
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
    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.

        Args:
            key: Object key.

        Raises:
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
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
    def scan(self, prefix: str) -> Iterable[str]:
        """
        Iterate all keys within prefix.

        Args:
            prefix: Prefix to scan.

        Returns:
            Yields matched keys.

        Raises:
            BlobError: On backend or I/O failure.
        """

    def __getitem__(self, key: str) -> bytes:
        """
        Retrieve binary data by key using dict-like access.

        This is a convenience wrapper over `get()`.

        Args:
            key: Object key.

        Returns:
            Binary data associated with the key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """
        return self.get(key)

    def __setitem__(self, key: str, data: bytes) -> None:
        """
        Store binary data under a key using dict-like assignment.

        This is a convenience wrapper over `put()`.

        If the key already exists, its value is overwritten.

        Args:
            key: Object key.
            data: Binary payload.

        Raises:
            BlobError: On backend or I/O failure.
        """
        self.put(key, data)

    def __delitem__(self, key: str) -> None:
        """
        Delete a key from the blob store using dict-like syntax.

        This is a convenience wrapper over `delete()`.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """
        self.delete(key)

    def __contains__(self, item: str) -> bool:
        """
        Check whether a key exists in the blob store.

        Implements the `in` operator:

            key in blob

        This is a convenience wrapper over `exists()`.

        Args:
            item: Object key.

        Returns:
            True if the key exists, False otherwise.

        Raises:
            BlobError: On backend or I/O failure.
        """
        return self.exists(item)


loader = Loader[type[BlobBase]](base="gufo.blob.sync", exclude=["base"])


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
        sqlite:///var/data/blob.db

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
