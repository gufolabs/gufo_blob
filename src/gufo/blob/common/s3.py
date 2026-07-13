# ---------------------------------------------------------------------
# Gufo Blob: S3 -- common protocol & utilities
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""Common S3 definitions and utilities."""

# Python modules
from __future__ import annotations

import re
import xml.parsers.expat
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

# Gufo Blob modules
from ..error import BlobError

DEFAULT_REGION = "us-east-1"

# S3 HTTP status codes
S3_OK = 200              # GET, HEAD success; scan page returned
S3_CREATED = 201         # PUT object created / overwritten
S3_DELETED = 204         # DELETE object removed safely

# URL-safe characters for S3 key encoding (RFC 6901 + S3 spec)
# https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
S3_SAFE_CHARS = "-_.~!*()*'/"

# Bucket name regex: 3-63 chars, lowercase letters/digits/dots/hyphens,
# must start/end with letter or digit (RFC 952 + S3 restrictions)
rx_bucket = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$")


def _is_ns(tag: str, ns: str, name: str) -> bool:
    """Match expat tag against namespace URI + local name.

    When expat is created with ``namespace_prefixes=1``, tags appear as
    the literal concatenation of the namespace URI and local name.  This
    helper also matches against a bare *name* for responses that omit
    namespaces entirely.

    Args:
        tag: Tag string emitted by the expat handler.
        ns: The S3 XML namespace URI.
        name: Local element name (e.g. ``"Code"``).

    Returns:
         True when *tag* matches either format.
    """
    return tag == f"{ns}{name}" or tag == name


class S3Xml:
    """Parse XML responses from S3-compatible API."""

    _NS = "http://s3.amazonaws.com/doc/2006-03-01/"

    @classmethod
    def list_objects(
        cls, body: bytes
    ) -> tuple[list[str], str | None]:
        """Parse ListObjectsV2 response.

        Args:
            body: XML body with object listings.

        Returns:
            Tuple of (list_of_keys, next_continuation_token_or_none).

        Raises:
            BlobError: on malformed XML response.
        """
        keys: list[str] = []
        key_buf: list[str] = []
        token: str | None = None
        token_buf: list[str] = []

        in_contents = False
        in_key = False
        in_token = False

        def _start(tag: str, _attrs: dict[str, str]) -> None:
            nonlocal in_contents, in_key, in_token
            if _is_ns(tag, cls._NS, "Contents"):
                in_contents = True
            elif in_contents and _is_ns(tag, cls._NS, "Key"):
                in_key = True
                key_buf.clear()
            elif _is_ns(tag, cls._NS, "NextContinuationToken"):
                in_token = True
                token_buf.clear()

        def _data(data: str) -> None:
            if in_key:
                key_buf.append(data)
            elif in_token:
                token_buf.append(data)

        def _end(tag: str) -> None:
            nonlocal in_contents, in_key, in_token, token
            if in_key and _is_ns(tag, cls._NS, "Key"):
                text = "".join(key_buf)
                if text:
                    keys.append(text)
                in_key = False
            elif in_token and _is_ns(tag, cls._NS, "NextContinuationToken"):
                token = "".join(token_buf) or None
                in_token = False
            elif _is_ns(tag, cls._NS, "Contents"):
                in_contents = False

        # Expat with namespace_prefixes=1 returns "urilocal" format
        parser = xml.parsers.expat.ParserCreate(
            "UTF-8", namespace_prefixes=1,
        )
        parser.StartElementHandler = _start
        parser.CharacterDataHandler = _data
        parser.EndElementHandler = _end
        try:
            parser.Parse(body)
        except xml.parsers.expat.ExpatError as ex:
            raise BlobError(
                f"Failed to parse S3 response: {ex.msg}",
            ) from ex

        return keys, token


class S3Error:
    """Parse error responses from S3-compatible API."""

    _NS = "http://s3.amazonaws.com/doc/2006-03-01/"

    @classmethod
    def from_xml(cls, body: bytes) -> BlobError:
        """Parse S3 XML error response into a BlobError.

        Args:
            body: XML error body.

        Returns:
            BlobError with parsed message.
        """
        code_parts: list[str] = []
        msg_parts: list[str] = []
        in_code = False
        in_msg = False

        def _start(tag: str, _attrs: dict[str, str]) -> None:
            nonlocal in_code, in_msg
            if _is_ns(tag, cls._NS, "Code") or tag == "Code":
                in_code = True
                code_parts.clear()
            elif _is_ns(tag, cls._NS, "Message") or tag == "Message":
                in_msg = True
                msg_parts.clear()

        def _data(data: str) -> None:
            if in_code:
                code_parts.append(data)
            elif in_msg:
                msg_parts.append(data)

        def _end(tag: str) -> None:
            nonlocal in_code, in_msg
            if in_code and (_is_ns(tag, cls._NS, "Code") or tag == "Code"):
                in_code = False
            if in_msg and (
                _is_ns(tag, cls._NS, "Message") or tag == "Message"
            ):
                in_msg = False

        parser = xml.parsers.expat.ParserCreate(
            "UTF-8", namespace_prefixes=1,
        )
        parser.StartElementHandler = _start
        parser.CharacterDataHandler = _data
        parser.EndElementHandler = _end
        try:
            parser.Parse(body)
        except xml.parsers.expat.ExpatError:
            return BlobError("S3 returned an unparsable error response")

        code = "".join(code_parts) or "Unknown"
        message = "".join(msg_parts)
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

    prefix = (u.path or "").lstrip("/").replace("//", "/")
    while "//" in prefix:
        prefix = prefix.replace("//", "/")
    if prefix:
        # S3 key path-safe characters
        safe_chars = r"-_.~!*()*\/" + chr(39)
        prefix = quote(prefix, safe=safe_chars)

    return {
        "bucket": bucket,
        "prefix": prefix,
        "endpoint": endpoint,
        "region": region,
        "access_key": access_key or None,
        "secret_key": secret_key_val or None,
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

    def __init__(    # noqa: PLR0913
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
            parts.append(p)
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
