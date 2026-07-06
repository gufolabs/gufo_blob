# ---------------------------------------------------------------------
# Gufo Blob: Synchronous memory backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.error import BlobError
from gufo.blob.sync.memory import MemoryBlob

# ----------------------------------------------------------------------
# basic put/get
# ----------------------------------------------------------------------


def test_put_and_get() -> None:
    b = MemoryBlob()

    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite() -> None:
    b = MemoryBlob()

    b.put("a", b"123")
    b.put("a", b"456")

    assert b.get("a") == b"456"


# ----------------------------------------------------------------------
# KeyError semantics
# ----------------------------------------------------------------------


def test_get_missing_key() -> None:
    b = MemoryBlob()

    with pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key() -> None:
    b = MemoryBlob()

    with pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key() -> None:
    b = MemoryBlob()

    with pytest.raises(KeyError):
        del b["missing"]


# ----------------------------------------------------------------------
# exists / contains
# ----------------------------------------------------------------------


def test_exists_and_contains() -> None:
    b = MemoryBlob()

    assert not b.exists("a")
    assert "a" not in b

    b.put("a", b"1")

    assert b.exists("a")
    assert "a" in b


# ----------------------------------------------------------------------
# delete
# ----------------------------------------------------------------------


def test_delete() -> None:
    b = MemoryBlob()

    b.put("a", b"123")
    b.delete("a")

    with pytest.raises(KeyError):
        b.get("a")


# ----------------------------------------------------------------------
# scan (prefix)
# ----------------------------------------------------------------------


def test_scan_prefix() -> None:
    b = MemoryBlob()

    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")

    result = sorted(b.scan("a/"))

    assert result == ["a/1", "a/2"]


def test_scan_empty_prefix_returns_all() -> None:
    b = MemoryBlob()

    b.put("a", b"x")
    b.put("b", b"x")

    result = sorted(b.scan(""))

    assert result == ["a", "b"]


# ----------------------------------------------------------------------
# max_objects limit
# ----------------------------------------------------------------------


def test_max_objects_limit() -> None:
    b = MemoryBlob(max_objects=2)

    b.put("a", b"1")
    b.put("b", b"1")

    with pytest.raises(BlobError):
        b.put("c", b"1")


def test_max_objects_update_does_not_count_extra() -> None:
    b = MemoryBlob(max_objects=1)

    b.put("a", b"1")
    b.put("a", b"2")  # overwrite should NOT increase object count


# ----------------------------------------------------------------------
# max_size limit
# ----------------------------------------------------------------------


def test_max_size_limit_insert() -> None:
    b = MemoryBlob(max_size=3)

    b.put("a", b"123")

    with pytest.raises(BlobError):
        b.put("b", b"4")  # total would exceed 3


def test_max_size_limit_update() -> None:
    b = MemoryBlob(max_size=3)

    b.put("a", b"12")
    b.put("a", b"123")  # allowed (delta = +1)

    assert b.get("a") == b"123"


def test_max_size_limit_reduce_on_update() -> None:
    b = MemoryBlob(max_size=10)

    b.put("a", b"1234")
    b.put("a", b"1")  # should reduce total size

    assert b.get("a") == b"1"


# ----------------------------------------------------------------------
# combined constraints
# ----------------------------------------------------------------------


def test_combined_limits() -> None:
    b = MemoryBlob(max_objects=2, max_size=10)

    b.put("a", b"123")
    b.put("b", b"123")

    with pytest.raises(BlobError):
        b.put("c", b"1")


# ----------------------------------------------------------------------
# dict sugar
# ----------------------------------------------------------------------


def test_dict_api() -> None:
    b = MemoryBlob()

    b["a"] = b"123"
    assert b["a"] == b"123"

    del b["a"]

    with pytest.raises(KeyError):
        _ = b["a"]


# ----------------------------------------------------------------------
# properties
# ----------------------------------------------------------------------


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


# URL parsing


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
