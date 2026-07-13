# ---------------------------------------------------------------------
# Gufo Blob: Async S3 backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""Test S3 async backend."""

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.aio.s3 import S3Blob

from .helpers.s3d import S3Info
from .utils import sort_async_iterable


@pytest.mark.asyncio
async def test_put_and_get(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a", b"123")
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a", b"123")
    await b.put("a", b"456")
    assert await b.get("a") == b"456"


@pytest.mark.asyncio
async def test_nested_put(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    items = ["a/b/1", "a/2", "a/b/3", "a/b/c/4"]
    for n, item in enumerate(items):
        await b.put(item, chr(n).encode())
    for n, item in enumerate(items):
        assert await b.get(item) == chr(n).encode()


@pytest.mark.asyncio
async def test_put_empty_data(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a", b"")
    assert await b.get("a") == b""


@pytest.mark.asyncio
async def test_get_missing_key(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    with pytest.raises(KeyError):
        await b.get("missing")


@pytest.mark.asyncio
async def test_delete_missing_key(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    with pytest.raises(KeyError):
        await b.delete("missing")


@pytest.mark.asyncio
async def test_delitem_missing_key(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    with pytest.raises(KeyError):
        del b["missing"]


@pytest.mark.asyncio
async def test_exists_and_contains(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    assert not await b.exists("a")
    await b.put("a", b"1")
    assert await b.exists("a")


@pytest.mark.asyncio
async def test_delete(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a", b"123")
    await b.delete("a")
    with pytest.raises(KeyError):
        await b.get("a")


@pytest.mark.asyncio
async def test_scan_prefix(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a/1", b"x")
    await b.put("a/2", b"x")
    await b.put("b/1", b"x")
    result = await sort_async_iterable(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
async def test_scan_empty_prefix_returns_all(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    await b.put("a", b"x")
    await b.put("b", b"x")
    result = await sort_async_iterable(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_scan_empty_table(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    result = await sort_async_iterable(b.scan(""))
    assert result == []


@pytest.mark.asyncio
async def test_dict_api(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
      )
    b["a"] = b"123"
    assert b["a"] == b"123"
    del b["a"]
    with pytest.raises(KeyError):
        _ = b["a"]


@pytest.mark.asyncio
async def test_scan_with_prefix(s3info: S3Info) -> None:
    b = S3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
        prefix="ns1",
      )
    await b.put("obj1", b"data1")
    await b.put("obj2/sub", b"data2")
    result = await sort_async_iterable(b.scan(""))
    assert result == ["obj1", "obj2/sub"]
