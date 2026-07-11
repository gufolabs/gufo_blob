# ---------------------------------------------------------------------
# Gufo Blob: Synchronous API tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from collections.abc import Iterator
from contextlib import contextmanager
from tempfile import TemporaryDirectory

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.sync import open_blob
from gufo.blob.sync.base import BlobBase

from .helpers.ftpd import FTPInfo

V_TMP = "${TMP}"
V_FTP = "ftp://${FTP}"


@pytest.fixture(
    params=[
        "${TMP}",
        "file://${TMP}",
        "memory:///",
        "sqlite:///${TMP}/blob.db",
        "ftp://${FTP}",
    ]
)
def blob_url(request: pytest.FixtureRequest, ftpinfo: FTPInfo) -> str:
    url = request.param
    if url == V_FTP:
        return ftpinfo.url
    return url


@contextmanager
def prepare_blob(url: str) -> Iterator[BlobBase]:
    """
    Setup test blob context according url.

    Replaces:
    - `${TMP}` with temporary directory
    """
    if V_TMP in url:
        with TemporaryDirectory() as tmp:
            ctx_url = url.replace(V_TMP, str(tmp))
            with open_blob(ctx_url) as blob:
                yield blob
    else:
        with open_blob(url) as blob:
            yield blob


def test_put_and_get(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a", b"123")
        assert b.get("a") == b"123"


def test_overwrite(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a", b"123")
        b.put("a", b"456")
        assert b.get("a") == b"456"


def test_put_empty_data(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a", b"")
        assert b.get("a") == b""


def test_get_missing_key(blob_url: str) -> None:
    with prepare_blob(blob_url) as b, pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key(blob_url: str) -> None:
    with prepare_blob(blob_url) as b, pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key(blob_url: str) -> None:
    with prepare_blob(blob_url) as b, pytest.raises(KeyError):
        del b["missing"]


def test_exists_and_contains(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        assert not b.exists("a")
        assert "a" not in b

        b.put("a", b"1")

        assert b.exists("a")
        assert "a" in b


def test_delete(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a", b"123")
        b.delete("a")

        with pytest.raises(KeyError):
            b.get("a")


def test_scan_prefix(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a/1", b"x")
        b.put("a/2", b"x")
        b.put("b/1", b"x")
        result = sorted(b.scan("a/"))
        assert result == ["a/1", "a/2"]


def test_scan_empty_prefix_returns_all(blob_url: str) -> None:
    with prepare_blob(blob_url) as b:
        b.put("a", b"x")
        b.put("b", b"x")
        result = sorted(b.scan(""))
        assert result == ["a", "b"]
