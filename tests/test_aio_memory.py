# ---------------------------------------------------------------------
# Gufo Blob: Async memory backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

from gufo.blob.aio.memory import MemoryBlob

# Gufo Blob modules
from gufo.blob.error import BlobError

from .utils import sort_async_iterable


@pytest.mark.asyncio
async def test_put_and_get() -> None:
    b = MemoryBlob()

    await b.put("a", b"123")
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite() -> None:
    b = MemoryBlob()

    await b.put("a", b"123")
    await b.put("a", b"456")

    assert await b.get("a") == b"456"


@pytest.mark.asyncio
async def test_put_empty_data() -> None:
    b = MemoryBlob()

    await b.put("empty", b"")

    assert await b.get("empty") == b""


@pytest.mark.asyncio
async def test_get_missing_key() -> None:
    b = MemoryBlob()

    with pytest.raises(KeyError):
        await b.get("missing")


@pytest.mark.asyncio
async def test_delete_missing_key() -> None:
    b = MemoryBlob()

    with pytest.raises(KeyError):
        await b.delete("missing")


@pytest.mark.asyncio
async def test_exists_and_contains() -> None:
    b = MemoryBlob()
    assert not await b.exists("a")
    await b.put("a", b"1")
    assert await b.exists("a")


@pytest.mark.asyncio
async def test_delete() -> None:
    b = MemoryBlob()
    await b.put("a", b"123")
    await b.delete("a")
    with pytest.raises(KeyError):
        await b.get("a")


@pytest.mark.asyncio
async def test_scan_prefix() -> None:
    b = MemoryBlob()
    await b.put("a/1", b"x")
    await b.put("a/2", b"x")
    await b.put("b/1", b"x")
    result = await sort_async_iterable(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
async def test_scan_empty_prefix_returns_all() -> None:
    b = MemoryBlob()
    await b.put("a", b"x")
    await b.put("b", b"x")

    result = await sort_async_iterable(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_max_objects_limit() -> None:
    b = MemoryBlob(max_objects=2)
    await b.put("a", b"1")
    await b.put("b", b"1")
    with pytest.raises(BlobError):
        await b.put("c", b"1")


@pytest.mark.asyncio
async def test_max_objects_update_does_not_count_extra() -> None:
    b = MemoryBlob(max_objects=1)
    await b.put("a", b"1")
    await b.put("a", b"2")  # overwrite should NOT increase object count


@pytest.mark.asyncio
async def test_max_size_limit_insert() -> None:
    b = MemoryBlob(max_size=3)
    await b.put("a", b"123")
    with pytest.raises(BlobError):
        await b.put("b", b"4")  # total would exceed 3


@pytest.mark.asyncio
async def test_max_size_limit_update() -> None:
    b = MemoryBlob(max_size=3)
    await b.put("a", b"12")
    await b.put("a", b"123")  # allowed (delta = +1)
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_max_size_limit_reduce_on_update() -> None:
    b = MemoryBlob(max_size=10)
    await b.put("a", b"1234")
    await b.put("a", b"1")  # should reduce total size
    assert await b.get("a") == b"1"


@pytest.mark.asyncio
async def test_combined_limits() -> None:
    b = MemoryBlob(max_objects=2, max_size=10)

    await b.put("a", b"123")
    await b.put("b", b"123")

    with pytest.raises(BlobError):
        await b.put("c", b"1")


def test_max_objects_property() -> None:
    b = MemoryBlob(max_objects=10)
    assert b.max_objects == 10


def test_max_objects_none() -> None:
    b = MemoryBlob()
    assert b.max_objects is None


def test_max_size_property() -> None:
    b = MemoryBlob(max_size=1024)
    assert b.max_size == 1024


def test_max_size_none() -> None:
    b = MemoryBlob()
    assert b.max_size is None


def test_from_url_empty_scheme() -> None:
    b = MemoryBlob.from_url("memory://")
    assert isinstance(b, MemoryBlob)
    assert b.max_objects is None
    assert b.max_size is None


def test_from_url_max_objects() -> None:
    b = MemoryBlob.from_url("memory://?max_objects=10")
    assert b.max_objects == 10
    assert b.max_size is None


def test_from_url_max_size() -> None:
    b = MemoryBlob.from_url("memory://?max_size=2048")
    assert b.max_objects is None
    assert b.max_size == 2048


def test_from_url_both_params() -> None:
    b = MemoryBlob.from_url("memory://?max_objects=5&max_size=100")
    assert b.max_objects == 5
    assert b.max_size == 100


def test_from_url_invalid_int() -> None:
    with pytest.raises(BlobError):
        MemoryBlob.from_url("memory://?max_size=abc")


def test_from_url_unknown_scheme() -> None:
    with pytest.raises(BlobError):
        MemoryBlob.from_url("unknown://")
