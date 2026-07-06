# ---------------------------------------------------------------------
# Gufo Blob: Synchronous memory backend
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""MemoryBlob implementation."""

# Python modules
from __future__ import annotations

from collections.abc import Iterable
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse

# Gufo Blob modules
from ..error import BlobError
from .base import BlobBase


class MemoryBlob(BlobBase):
    """
    In-memory implementation of Blob storage.

    Stores all objects in process memory with optional limits:
      - max_objects: maximum number of keys allowed
      - max_size: maximum total size of all stored values in bytes
    """

    name = "memory"

    def __init__(
        self, max_objects: int | None = None, max_size: int | None = None
    ) -> None:
        self._data: dict[str, bytes] = {}
        self._max_objects = max_objects
        self._max_size = max_size
        self._size = 0  # total bytes of all values
        self._data_lock = Lock()

    @property
    def max_objects(self) -> int | None:
        """
        Maximum number of objects allowed in the blob store.

        If set to None, the number of objects is unlimited.

        Returns:
            Maximum number of stored keys or None if unlimited.
        """
        return self._max_objects

    @property
    def max_size(self) -> int | None:
        """
        Maximum total size of all stored values in bytes.

        If set to None, total storage size is unlimited.

        Returns:
            Maximum total size in bytes or None if unlimited.
        """
        return self._max_size

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """
        Parse URL and extract parameters for constructor.

        Args:
            url: URL to parse.

        Returns:
            `**kwargs` for constructor.
        """
        parsed = urlparse(url)

        # schema validation
        if parsed.scheme not in ("memory", "", None):
            msg = f"unsupported schema: {parsed.scheme}"
            raise BlobError(msg)

        params = parse_qs(parsed.query)

        def get_int(name: str) -> int | None:
            v = params.get(name)
            if not v:
                return None
            try:
                return int(v[0])
            except ValueError as e:
                msg = f"invalid int param {name}={v[0]}"
                raise BlobError(msg) from e

        return {
            "max_objects": get_int("max_objects"),
            "max_size": get_int("max_size"),
        }

    def _check_limits(self, new_key: str | None, new_size: int) -> None:
        """
        Validate storage capacity constraints before applying an update.

        This method enforces optional resource limits defined for the blob
        instance:

        - max_objects: maximum number of distinct keys allowed
        - max_size: maximum total size (in bytes) of all stored values

        The check is performed against a *projected state*, meaning that
        both new inserts and updates are taken into account:
        - For new keys, object count is incremented.
        - For existing keys, the old value size is replaced with the new one.

        Args:
            new_key: Target key being written. If None, only size validation
                is performed.
            new_size: Size in bytes of the new value.

        Raises:
            BlobError: If applying the operation would exceed configured
                capacity limits.
        """
        current_objects = len(self._data)
        current_size = self._size

        # object limit
        if self._max_objects is not None:
            is_new = new_key is None or new_key not in self._data
            if is_new and current_objects + 1 > self._max_objects:
                msg = "max_objects limit exceeded"
                raise BlobError(msg)

        # size limit
        if self._max_size is not None:
            # if updating existing key → subtract old size
            old_size = len(self._data.get(new_key, b"")) if new_key else 0
            projected = current_size - old_size + new_size

            if projected > self._max_size:
                msg = "max_size limit exceeded"
                raise BlobError(msg)

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
        with self._data_lock:
            old = self._data.get(key)
            new_size = len(data)
            self._check_limits(key, new_size)
            if old is None:
                self._size += new_size
            else:
                self._size += new_size - len(old)
            self._data[key] = data

    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.

        Args:
            key: Object key.

        Raises:
            BlobError: On backend or I/O failure.
        """
        try:
            with self._data_lock:
                return self._data[key]
        except KeyError as e:
            raise KeyError(key) from e

    def delete(self, key: str) -> None:
        """
        Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """
        with self._data_lock:
            try:
                data = self._data.pop(key)
            except KeyError as e:
                raise KeyError(key) from e
            self._size -= len(data)

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
        with self._data_lock:
            return key in self._data

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
        with self._data_lock:
            data = [k for k in self._data if k.startswith(prefix)]
        yield from data
