# ---------------------------------------------------------------------
# Gufo Blob: Synchronous file backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from pathlib import Path

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.sync.file import FileBlob


def test_put_get(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("a", b"123")
    b.put("a", b"456")

    assert b.get("a") == b"456"


def test_put_empty_data(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("empty", b"")

    assert b.get("empty") == b""


def test_missing_key_get(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    with pytest.raises(KeyError):
        b.get("missing")


def test_missing_key_delete(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    with pytest.raises(KeyError):
        b.delete("missing")


def test_exists(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    assert not b.exists("a")

    b.put("a", b"1")

    assert b.exists("a")
    assert "a" in b


def test_delete(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("a", b"123")
    b.delete("a")

    with pytest.raises(KeyError):
        b.get("a")


def test_scan(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")

    result = sorted(b.scan("a/"))

    assert result == ["a/1", "a/2"]


def test_scan_all(tmp_dir: Path) -> None:
    b = FileBlob(str(tmp_dir))

    b.put("a", b"x")
    b.put("b", b"x")

    result = sorted(b.scan(""))

    assert result == ["a", "b"]


def test_from_url(tmp_dir: Path) -> None:
    b = FileBlob.from_url(f"file://{tmp_dir}")

    b.put("a", b"123")
    assert b.get("a") == b"123"
