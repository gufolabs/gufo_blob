# ---------------------------------------------------------------------
# Gufo Blob: Async FTP backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.aio.ftp import FTPBlob
from gufo.blob.common.ftp import FTPFeatures

from .helpers.ftpd import FTPInfo
from .utils import sort_async_iterable

TEST_SCAN_FEATURES = [
    FTPFeatures(),
    FTPFeatures(supports_mlsd=True, supports_mlst=True),
]
TEST_EXISTS_FEATURES = [
    FTPFeatures(),
    FTPFeatures(supports_mlsd=True, supports_mlst=True),
    FTPFeatures(supports_size=True),
]


# ----------------------------------------------------------------------
# basic put/get
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_and_get(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    await b.put("a", b"123")
    assert await b.get("a") == b"123"


@pytest.mark.asyncio
async def test_overwrite(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    await b.put("a", b"123")
    await b.put("a", b"456")
    assert await b.get("a") == b"456"


@pytest.mark.asyncio
async def test_nested_put(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    items = ["a/b/1", "a/2", "a/b/3", "a/b/c/4"]
    for n, item in enumerate(items):
        await b.put(item, chr(n).encode())
    for n, item in enumerate(items):
        assert await b.get(item) == chr(n).encode()


@pytest.mark.asyncio
async def test_put_empty_data(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    await b.put("a", b"")
    assert await b.get("a") == b""


@pytest.mark.asyncio
async def test_get_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    with pytest.raises(KeyError):
        await b.get("missing")


@pytest.mark.asyncio
async def test_delete_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    with pytest.raises(KeyError):
        await b.delete("missing")


@pytest.mark.asyncio
@pytest.mark.parametrize("features", TEST_EXISTS_FEATURES)
async def test_exists_and_contains(
    ftpinfo: FTPInfo, features: FTPFeatures
) -> None:
    b = ftpinfo.aio_blob_with_features(features)
    assert not await b.exists("a")
    await b.put("a", b"1")
    assert await b.exists("a")


@pytest.mark.asyncio
async def test_delete(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.aio_blob
    await b.put("a", b"123")
    await b.delete("a")
    with pytest.raises(KeyError):
        await b.get("a")


@pytest.mark.asyncio
@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
async def test_scan_prefix(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.aio_blob_with_features(features)
    await b.put("a/1", b"x")
    await b.put("a/2", b"x")
    await b.put("b/1", b"x")
    result = await sort_async_iterable(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
async def test_scan_empty_prefix_returns_all(
    ftpinfo: FTPInfo, features: FTPFeatures
) -> None:
    b = ftpinfo.aio_blob_with_features(features)
    await b.put("a", b"x")
    await b.put("b", b"x")
    result = await sort_async_iterable(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.asyncio
@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
async def test_scan_empty_table(
    ftpinfo: FTPInfo, features: FTPFeatures
) -> None:
    b = ftpinfo.aio_blob_with_features(features)
    result = await sort_async_iterable(b.scan(""))
    assert result == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "features",
    [
        FTPFeatures(
            supports_mlsd=False, supports_mlst=False, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=True, supports_mlst=False, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=False, supports_mlst=True, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=False, supports_mlst=False, supports_size=True
        ),
    ],
)
async def test_exists_impl(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = FTPBlob(
        host=ftpinfo.host,
        port=ftpinfo.port,
        user=ftpinfo.user,
        password=ftpinfo.password,
        timeout=1.0,
        features=features,
    )
    key1 = "a/b/c"
    await b.put(key1, b"xxx")
    assert (await b.exists(key1)) is True
    assert (await b.exists("a/b/d")) is False
    assert (await b.exists("a")) is False
    assert (await b.exists("a/b")) is False
    assert (await b.exists("b/c")) is False
