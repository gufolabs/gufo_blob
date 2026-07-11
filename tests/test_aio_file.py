# ---------------------------------------------------------------------
# Gufo Blob: Async file backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from pathlib import Path

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.aio.file import FileBlob

from .utils import sort_async_iterable


@pytest.mark.asyncio
async def test_put_get(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("a", b"123")
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("a", b"123")
    await b.put("a", b"456")

    assert await b.get("a") == b"456"


@pytest.mark.asyncio
async def test_put_empty_data(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("empty", b"")

    assert await b.get("empty") == b""


@pytest.mark.asyncio
async def test_missing_key_get(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    with pytest.raises(KeyError):
        await b.get("missing")


@pytest.mark.asyncio
async def test_missing_key_delete(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    with pytest.raises(KeyError):
        await b.delete("missing")


@pytest.mark.asyncio
async def test_exists(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    assert not await b.exists("a")

    await b.put("a", b"1")

    assert await b.exists("a")


@pytest.mark.asyncio
async def test_delete(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("a", b"123")
    await b.delete("a")

    with pytest.raises(KeyError):
        await b.get("a")


@pytest.mark.asyncio
async def test_scan(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("a/1", b"x")
    await b.put("a/2", b"x")
    await b.put("b/1", b"x")

    result = await sort_async_iterable(b.scan("a/"))

    assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
async def test_scan_all(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    await b.put("a", b"x")
    await b.put("b", b"x")

    result = await sort_async_iterable(b.scan(""))

    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_from_url(tmp_dir: Path) -> None:
    b = FileBlob.from_url(f"file://{tmp_dir}")

    await b.put("a", b"123")
    assert await b.get("a") == b"123"
