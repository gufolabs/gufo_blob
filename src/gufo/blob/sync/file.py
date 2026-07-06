# ---------------------------------------------------------------------
# Gufo Blob: Synchronous file backend
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""FileBlob implementation."""

# Python modules
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Gufo Blob modules
from gufo.blob.error import BlobError
from gufo.blob.sync.base import BlobBase


class FileBlob(BlobBase):
    """
    Filesystem-backed blob store.

    Stores binary objects on local filesystem under a fixed root
    directory.

    The API exposes a flat keyspace model. There are no directories
    in the logical model, only keys.

    All operations are sandboxed to prevent escaping the root directory
    via path traversal or absolute paths.
    """

    name = "file"

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        if not self._root.exists() or not self._root.is_dir():
            msg = f"invalid root directory: {root}"
            raise BlobError(msg)

    def _resolve(self, key: str) -> Path:
        """
        Resolve blob key into safe filesystem path.

        Enforces:
        - no absolute paths
        - no path traversal (..)
        - all paths must stay inside root directory
        - optional prefix namespace
        """
        if not key or key.startswith("/"):
            msg = f"invalid key: {key}"
            raise BlobError(msg)
        path = (self._root / key).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as e:
            msg = f"key escapes storage root: {key}"
            raise BlobError(msg) from e
        return path

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

        if parsed.scheme not in ("file", ""):
            msg = f"invalid scheme: {parsed.scheme}"
            raise BlobError(msg)

        root = parsed.path or "/"
        return {"root": root}

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
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.

        Args:
            key: Object key.

        Raises:
            BlobError: On backend or I/O failure.
        """
        path = self._resolve(key)

        try:
            return path.read_bytes()
        except FileNotFoundError as e:
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
        path = self._resolve(key)

        try:
            path.unlink()
        except FileNotFoundError as e:
            raise KeyError(key) from e

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
        return self._resolve(key).exists()

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
        base = self._resolve(prefix) if prefix else self._root

        if not base.exists():
            return

        if base.is_file():
            yield base.relative_to(self._root).as_posix()
            return

        for p in base.rglob("*"):
            if p.is_file():
                yield p.relative_to(self._root).as_posix()
