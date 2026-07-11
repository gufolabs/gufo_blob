# ---------------------------------------------------------------------
# Gufo Blob: Async API tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from tempfile import TemporaryDirectory

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.aio import open_blob
from gufo.blob.aio.base import BlobBase

from .utils import sort_async_iterable

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


@asynccontextmanager
async def prepare_blob(url: str) -> AsyncIterator[BlobBase]:
    """
    Setup test blob context according url.

    Replaces:
    - `${TMP}` with temporary directory
    """
    if V_TMP in url:
        with TemporaryDirectory() as tmp:
            ctx_url = url.replace(V_TMP, str(tmp))
            async with open_blob(ctx_url) as blob:
                yield blob
    else:
        async with open_blob(url) as blob:
            yield blob


@pytest.mark.asyncio
async def test_put_and_get(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a", b"123")
        assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a", b"123")
        await b.put("a", b"456")
        assert await b.get("a") == b"456"


@pytest.mark.asyncio
async def test_put_empty_data(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a", b"")
        assert await b.get("a") == b""


@pytest.mark.asyncio
async def test_get_missing_key(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        with pytest.raises(KeyError):
            await b.get("missing")


@pytest.mark.asyncio
async def test_delete_missing_key(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        with pytest.raises(KeyError):
            await b.delete("missing")


@pytest.mark.asyncio
async def test_exists_and_contains(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        assert not await b.exists("a")
        await b.put("a", b"1")
        assert await b.exists("a")


@pytest.mark.asyncio
async def test_delete(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a", b"123")
        await b.delete("a")
        with pytest.raises(KeyError):
            await b.get("a")


@pytest.mark.asyncio
async def test_scan_prefix(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a/1", b"x")
        await b.put("a/2", b"x")
        await b.put("b/1", b"x")
        result = await sort_async_iterable(b.scan("a/"))
        assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
async def test_scan_empty_prefix_returns_all(blob_url: str) -> None:
    async with prepare_blob(blob_url) as b:
        await b.put("a", b"x")
        await b.put("b", b"x")
        result = await sort_async_iterable(b.scan(""))
        assert result == ["a", "b"]
