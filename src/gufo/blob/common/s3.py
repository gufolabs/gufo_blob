# ---------------------------------------------------------------------
# Gufo Blob: S3 -- common protocol & utilities
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""Common S3 definitions and utilities."""

# Python modules
from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import (
    parse_qs,
    parse_qsl,
    quote,
    unquote,
    urlparse,
    urlsplit,
)
from xml.parsers import expat

# Gufo Blob modules
from ..error import BlobError

DEFAULT_REGION = "us-east-1"

# S3 HTTP status codes
S3_OK = 200  # GET, HEAD success; scan page returned
S3_CREATED = 200  # PUT object created / overwritten
S3_DELETED = 204  # DELETE object removed safely
S3_NOT_FOUND = 404

# URL-safe characters for S3 key encoding (RFC 6901 + S3 spec)
# https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
S3_SAFE_CHARS = "-_.~!*()*'/"

# Bucket name regex: 3-63 chars, lowercase letters/digits/dots/hyphens,
# must start/end with letter or digit (RFC 952 + S3 restrictions)
rx_bucket = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$")


class S3Response(Protocol):
    """Subset of an HTTP response used by the S3 backend."""

    status: int
    content: bytes


def _parse_xml_fields(
    body: bytes,
    fields: set[tuple[str, ...]],
) -> dict[tuple[str, ...], list[str]]:
    """Parse selected element text from XML using Expat."""
    values = {field: [] for field in fields}
    path: list[str] = []
    active_field: tuple[str, ...] | None = None
    text: list[str] = []

    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _start(tag: str, _attrs: dict[str, str]) -> None:
        nonlocal active_field, text
        path.append(_local_name(tag))
        for field in fields:
            if len(path) >= len(field) and tuple(path[-len(field) :]) == field:
                active_field = field
                text = []
                break

    def _data(value: str) -> None:
        if active_field is not None:
            text.append(value)

    def _end(tag: str) -> None:
        nonlocal active_field, text
        if active_field is not None and path[-len(active_field) :] == list(
            active_field
        ):
            values[active_field].append("".join(text))
            active_field = None
            text = []
        path.pop()

    parser = expat.ParserCreate("UTF-8", "}")
    parser.StartElementHandler = _start
    parser.CharacterDataHandler = _data
    parser.EndElementHandler = _end
    parser.Parse(body, True)
    return values


class S3Xml:
    """Parse XML responses from S3-compatible API."""

    @classmethod
    def list_objects(cls, body: bytes) -> tuple[list[str], str | None]:
        """Parse ListObjectsV2 response.

        Args:
            body: XML body with object listings.

        Returns:
            Tuple of (list_of_keys, next_continuation_token_or_none).

        Raises:
            BlobError: on malformed XML response.
        """
        fields = {
            ("Contents", "Key"),
            ("ListBucketResult", "NextContinuationToken"),
        }
        try:
            values = _parse_xml_fields(body, fields)
        except expat.ExpatError as ex:
            msg = f"Failed to parse S3 response: {ex}"
            raise BlobError(msg) from ex

        keys = [key for key in values[("Contents", "Key")] if key]
        tokens = values[("ListBucketResult", "NextContinuationToken")]
        token = tokens[0] if tokens and tokens[0] else None
        return keys, token


class S3Error:
    """Parse error responses from S3-compatible API."""

    @classmethod
    def from_xml(cls, body: bytes) -> BlobError:
        """Parse S3 XML error response into a BlobError.

        Args:
            body: XML error body.

        Returns:
            BlobError with parsed message.
        """
        fields = {("Error", "Code"), ("Error", "Message")}
        try:
            values = _parse_xml_fields(body, fields)
        except expat.ExpatError:
            return BlobError("S3 returned an unparsable error response")

        code = next(iter(values[("Error", "Code")]), "") or "Unknown"
        message = next(iter(values[("Error", "Message")]), "")
        return BlobError(f"S3 error {code}: {message}")


def parse_url(url: str) -> dict[str, Any]:
    """Parse S3 URL and extract parameters for the constructor.

    Accepts ``s3://bucket/path`` URLs with optional query params::

        s3://mybucket/prefix?endpoint=http://127.0.0.1:5555&region=us-east-1

    Args:
        url: S3-compatible URL.

    Returns:
         ``**kwargs`` for the backend constructor.

    Raises:
        BlobError: on unsupported schemas or missing bucket name.
    """
    u = urlparse(url)
    if u.scheme != "s3":
        msg = f"invalid scheme: {u.scheme!r}"
        raise BlobError(msg)

    bucket = unquote(u.hostname or "")
    if not bucket:
        msg = "bucket name is required"
        raise BlobError(msg)

    qs = parse_qs(u.query, keep_blank_values=True)
    endpoint = qs.get("endpoint", [""])[0]
    region = qs.get("region", [DEFAULT_REGION])[0]
    access_key = qs.get("access_key", [""])[0]
    secret_key_val = qs.get("secret_key", [""])[0]

    if not rx_bucket.fullmatch(bucket):
        msg = f"invalid bucket name: {bucket!r}"
        raise BlobError(msg)

    prefix = unquote((u.path or "").lstrip("/"))
    while "//" in prefix:
        prefix = prefix.replace("//", "/")
    return {
        "bucket": bucket,
        "prefix": prefix,
        "endpoint": endpoint,
        "region": region,
        "access_key": access_key or None,
        "secret_key": secret_key_val or None,
    }


def sign_request(
    method: str,
    url: str,
    body: bytes,
    region: str,
    credentials: tuple[str | None, str | None],
) -> dict[str, bytes]:
    """Create SigV4 headers when credentials are configured."""
    access_key, secret_key = credentials
    if not access_key or not secret_key:
        return {}

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    payload_hash = hashlib.sha256(body).hexdigest()
    headers = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    canonical_headers = "".join(
        f"{k}:{v}\n" for k, v in sorted(headers.items())
    )
    signed_headers = ";".join(sorted(headers))
    canonical_uri = quote(unquote(parsed.path or "/"), safe="/-_.~")
    query_items = sorted(
        (
            quote(k, safe="-_.~"),
            quote(v, safe="-_.~"),
        )
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
    )
    canonical_query = "&".join(f"{k}={v}" for k, v in query_items)
    canonical_request = "\n".join(
        (
            method.upper(),
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )
    scope = f"{date}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        )
    )

    def _hmac(key: bytes, value: str) -> bytes:
        return hmac.new(key, value.encode(), hashlib.sha256).digest()

    signing_key = _hmac(
        _hmac(
            _hmac(
                _hmac(("AWS4" + secret_key).encode(), date),
                region,
            ),
            "s3",
        ),
        "aws4_request",
    )
    signature = hmac.new(
        signing_key, string_to_sign.encode(), hashlib.sha256
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "x-amz-content-sha256": payload_hash.encode(),
        "x-amz-date": amz_date.encode(),
        "authorization": authorization.encode(),
    }


class S3Info:
    """Information about an S3-compatible service connection.

    Attributes:
        host: Server hostname or address.
        port: Server port.
        bucket: Bucket name used for this connection.
        prefix: Optional key prefix within the bucket.
        access_key: AWS access key (optional).
        secret_key: AWS secret key (optional).
    """

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int,
        bucket: str,
        prefix: str = "",
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.bucket = bucket
        self.prefix = prefix
        self.access_key = access_key
        self.secret_key = secret_key

    @property
    def endpoint(self) -> str:
        """Build the S3-compatible endpoint URL."""
        return f"http://{self.host}:{self.port}"

    def url(self, *, prefix: str | None = None) -> str:
        """Build full connection URL for gufo.blob backends.

        Args:
            prefix: Override default key prefix.
        """
        p = prefix if prefix is not None else self.prefix
        parts: list[str] = [f"s3://{self.bucket}"]
        if p:
            parts.append(f"/{quote(p.lstrip('/'), safe=S3_SAFE_CHARS)}")
        extras: list[str] = []
        if self.endpoint:
            extras.append(f"endpoint={self.endpoint}")
        if self.access_key:
            ak_q = quote(self.access_key, safe=S3_SAFE_CHARS)
            extras.append(f"access_key={ak_q}")
        if self.secret_key:
            sk_q = quote(self.secret_key, safe=S3_SAFE_CHARS)
            extras.append(f"secret_key={sk_q}")
        if extras:
            parts.append("?")
            parts.append("&".join(extras))
        return "".join(parts)

    def clone(self) -> S3Info:
        """Return a shallow copy of this connection info.

        Returns:
            New S3Info with the same attributes.
        """
        return S3Info(
            host=self.host,
            port=self.port,
            bucket=self.bucket,
            prefix=self.prefix,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )
