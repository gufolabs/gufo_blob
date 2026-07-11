# ---------------------------------------------------------------------
# Gufo Blob: FTPBlob sync tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------


# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.common.ftp import FTPFeatures
from gufo.blob.sync.ftp import FTPBlob

from .helpers.ftpd import FTPInfo

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


def test_put_and_get(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    b.put("a", b"456")
    assert b.get("a") == b"456"


def test_nested_put(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    items = ["a/b/1", "a/2", "a/b/3", "a/b/c/4"]
    for n, item in enumerate(items):
        b.put(item, chr(n).encode())
    for n, item in enumerate(items):
        assert b.get(item) == chr(n).encode()


def test_put_empty_data(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"")
    assert b.get("a") == b""


def test_get_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        del b["missing"]


@pytest.mark.parametrize("features", TEST_EXISTS_FEATURES)
def test_exists_and_contains(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    assert not b.exists("a")
    assert "a" not in b
    b.put("a", b"1")
    assert b.exists("a")
    assert "a" in b


def test_delete(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    b.delete("a")
    with pytest.raises(KeyError):
        b.get("a")


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_prefix(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")
    result = sorted(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_empty_prefix_returns_all(
    ftpinfo: FTPInfo, features: FTPFeatures
) -> None:
    b = ftpinfo.blob_with_features(features)
    b.put("a", b"x")
    b.put("b", b"x")
    result = sorted(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_empty_table(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    result = sorted(b.scan(""))
    assert result == []


def test_dict_api(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b["a"] = b"123"
    assert b["a"] == b"123"
    del b["a"]
    with pytest.raises(KeyError):
        _ = b["a"]


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
def test_exists_impl(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = FTPBlob(
        host=ftpinfo.host,
        port=ftpinfo.port,
        user=ftpinfo.user,
        password=ftpinfo.password,
        timeout=1.0,
        features=features,
    )
    key1 = "a/b/c"
    b.put(key1, b"xxx")
    assert b.exists(key1) is True
    assert b.exists("a/b/d") is False
    assert b.exists("a") is False
    assert b.exists("a/b") is False
    assert b.exists("b/c") is False
