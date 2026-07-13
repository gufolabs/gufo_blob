# ---------------------------------------------------------------------
# Gufo Blob: S3 sync backend (via gufo.http)
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""Sync S3Blob implementation."""

# Python modules
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import quote

# Third-party modules
from gufo.http.sync_client import HttpClient as SyncClient

# Gufo Blob modules
from ..common.s3 import (
    S3_CREATED,
    S3_DELETED,
    S3_OK,
    S3Error,
    S3Xml,
    parse_url,
)
from .base import BlobBase


class S3Blob(BlobBase):
    """S3-compatible synchronous blob storage.

    Stores objects on an S3-compatible service using plain HTTP requests
    through ``gufo.http.sync_client.HttpClient``. No AWS SDK is used — all
    operations are standard REST calls.

    Args:
        bucket: Bucket name.
        prefix: Optional key prefix within the bucket.
        endpoint: Custom endpoint URL (e.g., MinIO or moto).
            If empty, uses default ``https://s3.amazonaws.com``.
        region: AWS region (default: ``us-east-1``).
        access_key: Access key ID (optional).
        secret_key: Secret access key (optional).
    """

    name = "s3"

    def __init__(  # noqa: PLR0913
        self,
        bucket: str,
        prefix: str = "",
        endpoint: str = "",
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix
        self._endpoint = endpoint or "https://s3.amazonaws.com"
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """Parse S3 URL and extract parameters for constructor.

        Args:
            url: S3 URL (e.g., ``s3://bucket/path``).

        Returns:
             ``**kwargs`` for the constructor.

        Raises:
            BlobError: on malformed URLs.
        """
        return parse_url(url)

    def _endpoint_host(self, key: str = "") -> str:
        """Build the request URL for an object or bucket operation.

        Args:
            key: Object key within the bucket (after prefix).

        Returns:
            Full URL to the S3 resource.
        """
        base = self._endpoint.rstrip("/")
        if self._prefix and not self._prefix.endswith("/"):
            full_key = f"{self._prefix}/{key}" if key else self._prefix
        elif self._prefix:
            full_key = f"{self._prefix}{key}" if key else self._prefix
        else:
            full_key = key
        return f"{base}/{self._bucket}/{full_key}".rstrip("/")

    def _list_url(self, prefix: str) -> str:
        """Build ListObjectsV2 URL.

        Args:
            prefix: S3 key prefix to list (after bucket prefix).

        Returns:
            Full URL with query parameters.
        """
        if self._prefix:
            if not self._prefix.endswith("/"):
                full = f"{self._prefix}/{prefix}"
            else:
                full = f"{self._prefix}{prefix}"
        else:
            full = prefix

        base = self._endpoint.rstrip("/")
        return (
            f"{base}/{self._bucket}?list-type=2&prefix={quote(full, safe='')}"
        )

    def _client(self) -> SyncClient:
        """Create or reuse an HTTP client."""
        return SyncClient()

    def put(self, key: str, data: bytes) -> None:
        """Store binary data under the given key.

        Sends a ``PUT`` request to create or overwrite the object.

        Args:
            key: Object key.
            data: Binary payload.

        Raises:
            BlobError: On backend or I/O failure.
        """
        url = self._endpoint_host(key)
        with self._client() as client:
            resp = client.put(url, data=data)
            if resp.status_code == S3_CREATED:
                return
            err = S3Error.from_xml(resp.content)
            raise err

    def get(self, key: str) -> bytes:
        """Retrieve data by key.

        Args:
            key: Object key.

        Returns:
            Stored bytes.

        Raises:
            KeyError: If the object does not exist.
            BlobError: On backend or I/O failure.
        """
        url = self._endpoint_host(key)
        with self._client() as client:
            resp = client.get(url)
            if resp.status_code == S3_OK:
                return resp.content
            err = S3Error.from_xml(resp.content)
            raise KeyError(key) from err

    def delete(self, key: str) -> None:
        """Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the object does not exist.
            BlobError: On backend or I/O failure.
        """
        url = self._endpoint_host(key)
        with self._client() as client:
            resp = client.delete(url)
            if resp.status_code == S3_DELETED:
                return
            err = S3Error.from_xml(resp.content)
            raise KeyError(key) from err

    def exists(self, key: str) -> bool:
        """Check whether a key exists in the blob store.

        Performs a ``HEAD`` request on the object.

        Args:
            key: Object key.

        Returns:
            True if the key exists, False otherwise.

        Raises:
            BlobError: On backend or I/O failure.
        """
        url = self._endpoint_host(key)
        with self._client() as client:
            resp = client.head(url)
            return resp.status_code == S3_OK

    def scan(self, prefix: str) -> Iterable[str]:
        """Iterate all keys within prefix.

        Uses ListObjectsV2 API with continuation tokens for pagination.

        Args:
            prefix: Prefix to scan (relative to bucket prefix).

        Returns:
            Yields matched keys (without bucket prefix).

        Raises:
            BlobError: On backend or I/O failure.
        """
        url = self._list_url(prefix)
        with self._client() as client:
            while True:
                resp = client.get(url)
                if resp.status_code != S3_OK:
                    err = S3Error.from_xml(resp.content)
                    raise err

                keys, token = S3Xml.list_objects(resp.content)
                for key in keys:
                    # Strip bucket prefix from returned keys
                    stripped = self._strip_prefix(key)
                    yield stripped

                if token:
                    url = (
                        f"{self._list_url(prefix)}&continuation-token={token}"
                    )
                else:
                    break

    def _strip_prefix(self, key: str) -> str:
        """Remove bucket prefix from a full S3 key.

        Args:
            key: Full S3 object key.

        Returns:
            Key with bucket prefix removed.
        """
        if not self._prefix:
            return key
        # Handle both cases: prefix with or without trailing slash
        prefix_raw = self._prefix
        if prefix_raw and not prefix_raw.endswith("/"):
            prefix_raw += "/"
        if key.startswith(prefix_raw):
            return key[len(prefix_raw) :]
        return key
