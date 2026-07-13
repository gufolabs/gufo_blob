# ---------------------------------------------------------------------
# Gufo Blob: Sync S3 backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""Test S3 sync backend."""

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.common.s3 import parse_url
from gufo.blob.error import BlobError
from gufo.blob.sync.s3 import S3Blob as SyncS3Blob

from .helpers.s3d import S3Info


def _make_blob(s3info: S3Info) -> SyncS3Blob:
   """Create a sync S3Blob for the given fixture."""
   return SyncS3Blob(
       bucket=s3info.bucket,
       endpoint=s3info.endpoint,
       access_key=s3info.access_key,
       secret_key=s3info.secret_key,
    )


def test_put_and_get(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a", b"123")
    b.put("a", b"456")
    assert b.get("a") == b"456"


def test_nested_put(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    items = ["a/b/1", "a/2", "a/b/3", "a/b/c/4"]
    for n, item in enumerate(items):
        b.put(item, chr(n).encode())
    for n, item in enumerate(items):
        assert b.get(item) == chr(n).encode()


def test_put_empty_data(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a", b"")
    assert b.get("a") == b""


def test_get_missing_key(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    with pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    with pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    with pytest.raises(KeyError):
        del b["missing"]


def test_exists_and_contains(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    assert not b.exists("a")
    assert "a" not in b
    b.put("a", b"1")
    assert b.exists("a")
    assert "a" in b


def test_delete(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a", b"123")
    b.delete("a")
    with pytest.raises(KeyError):
        b.get("a")


def test_scan_prefix(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")
    result = sorted(b.scan("a/"))
    assert result == ["a/1", "a/2"]


def test_scan_empty_prefix_returns_all(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b.put("a", b"x")
    b.put("b", b"x")
    result = sorted(b.scan(""))
    assert result == ["a", "b"]


def test_scan_empty_table(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    result = sorted(b.scan(""))
    assert result == []


def test_dict_api(s3info: S3Info) -> None:
    b = _make_blob(s3info)
    b["a"] = b"123"
    assert b["a"] == b"123"
    del b["a"]
    with pytest.raises(KeyError):
        _ = b["a"]


def test_from_url(s3info: S3Info) -> None:
    blob = SyncS3Blob.from_url(
        f"s3://testbucket/prefix?endpoint={s3info.endpoint}"
    )
    assert blob._prefix == "prefix"  # type: ignore[union-attr]


def test_scan_with_prefix(s3info: S3Info) -> None:
    b = SyncS3Blob(
        bucket=s3info.bucket,
        endpoint=s3info.endpoint,
        access_key=s3info.access_key,
        secret_key=s3info.secret_key,
        prefix="ns1",
    )
    b.put("obj1", b"data1")
    b.put("obj2/sub", b"data2")
    result = sorted(b.scan(""))
    assert result == ["obj1", "obj2/sub"]


def test_parse_url_invalid_scheme() -> None:
    with pytest.raises(BlobError):
        parse_url("http://bucket")


def test_parse_url_no_bucket() -> None:
    with pytest.raises(BlobError):
        parse_url("s3:///path")
