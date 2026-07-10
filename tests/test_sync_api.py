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

TEST_BACKENDS = [
    "${TMP}",
    "file://${TMP}",
    "memory:///",
    "sqlite:///${TMP}/blob.db",
]


V_TMP = "${TMP}"


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


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_put_and_get(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a", b"123")
        assert b.get("a") == b"123"


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_overwrite(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a", b"123")
        b.put("a", b"456")
        assert b.get("a") == b"456"


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_put_empty_data(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a", b"")
        assert b.get("a") == b""


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_get_missing_key(url: str) -> None:
    with prepare_blob(url) as b, pytest.raises(KeyError):
        b.get("missing")


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_delete_missing_key(url: str) -> None:
    with prepare_blob(url) as b, pytest.raises(KeyError):
        b.delete("missing")


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_delitem_missing_key(url: str) -> None:
    with prepare_blob(url) as b, pytest.raises(KeyError):
        del b["missing"]


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_exists_and_contains(url: str) -> None:
    with prepare_blob(url) as b:
        assert not b.exists("a")
        assert "a" not in b

        b.put("a", b"1")

        assert b.exists("a")
        assert "a" in b


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_delete(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a", b"123")
        b.delete("a")

        with pytest.raises(KeyError):
            b.get("a")


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_scan_prefix(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a/1", b"x")
        b.put("a/2", b"x")
        b.put("b/1", b"x")

        result = sorted(b.scan("a/"))

        assert result == ["a/1", "a/2"]


@pytest.mark.parametrize("url", TEST_BACKENDS)
def test_scan_empty_prefix_returns_all(url: str) -> None:
    with prepare_blob(url) as b:
        b.put("a", b"x")
        b.put("b", b"x")
        result = sorted(b.scan(""))
        assert result == ["a", "b"]
