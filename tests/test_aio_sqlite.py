# ---------------------------------------------------------------------
# Gufo Blob: Async sqlite backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from pathlib import Path

# Third-party modules
import pytest

from gufo.blob.aio.sqlite import (
    DEFAULT_KEY,
    DEFAULT_TABLE,
    DEFAULT_VALUE,
    SQLiteBlob,
)

# Gufo Blob modules
from .utils import sort_async_iterable

# ----------------------------------------------------------------------
# basic put/get
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_and_get(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    await b.put("a", b"123")
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    await b.put("a", b"123")
    await b.put("a", b"456")
    assert await b.get("a") == b"456"


# ----------------------------------------------------------------------
# KeyError semantics
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_missing_key(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    with pytest.raises(KeyError):
        await b.get("missing")


@pytest.mark.asyncio
async def test_delete_missing_key(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    with pytest.raises(KeyError):
        await b.delete("missing")


# ----------------------------------------------------------------------
# exists / contains
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exists_and_contains(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    assert not await b.exists("a")
    await b.put("a", b"1")
    assert await b.exists("a")


# ----------------------------------------------------------------------
# delete
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    await b.put("a", b"123")
    await b.delete("a")

    with pytest.raises(KeyError):
        await b.get("a")


@pytest.mark.asyncio
async def test_scan_prefix(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    await b.put("a/1", b"x")
    await b.put("a/2", b"x")
    await b.put("b/1", b"x")
    result = await sort_async_iterable(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
async def test_scan_empty_prefix_returns_all(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    await b.put("a", b"x")
    await b.put("b", b"x")
    result = await sort_async_iterable(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_scan_empty_table(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    result = await sort_async_iterable(b.scan(""))
    assert result == []


def test_parse_url_default() -> None:
    assert SQLiteBlob.parse_url("sqlite:///var/data/test.db") == {
        "path": "/var/data/test.db",
        "table": DEFAULT_TABLE,
        "key_col": DEFAULT_KEY,
        "value_col": DEFAULT_VALUE,
    }


def test_parse_url_custom() -> None:
    assert SQLiteBlob.parse_url(
        "sqlite:///var/data/test.db?table=t1&key=name&value=data"
    ) == {
        "path": "/var/data/test.db",
        "table": "t1",
        "key_col": "name",
        "value_col": "data",
    }


@pytest.mark.asyncio
async def test_custom_schema(tmp_path: Path) -> None:
    b = SQLiteBlob(
        tmp_path / "db.sqlite",
        table="objects",
        key_col="name",
        value_col="payload",
    )
    await b.put("k1", b"v1")
    assert await b.get("k1") == b"v1"


@pytest.mark.asyncio
async def test_reopen(tmp_path: Path) -> None:
    b = SQLiteBlob(tmp_path / "db.sqlite")
    await b.put("k", b"v")
    await b.close()

    b = SQLiteBlob(tmp_path / "db.sqlite")
    assert await b.get("k") == b"v"


@pytest.mark.asyncio
async def test_scan_prefix2(tmp_path: Path) -> None:
    b = SQLiteBlob(str(tmp_path / "db.sqlite"))
    await b.put("abc", b"")
    await b.put("abcd", b"")
    await b.put("abd", b"")
    await b.put("b", b"")
    r = await sort_async_iterable(b.scan("abc"))
    assert r == ["abc", "abcd"]


@pytest.mark.asyncio
async def test_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    a = SQLiteBlob(path)
    b = SQLiteBlob(path)
    await a.put("k", b"v")
    assert await b.get("k") == b"v"
    await b.put("k", b"x")
    assert await a.get("k") == b"x"
