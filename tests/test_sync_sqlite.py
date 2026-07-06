# ---------------------------------------------------------------------
# Gufo Blob: Synchronous sqlite backend tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from pathlib import Path

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.error import BlobError
from gufo.blob.sync.sqlite import (
    DEFAULT_KEY,
    DEFAULT_TABLE,
    DEFAULT_VALUE,
    SQLiteBlob,
)

# ----------------------------------------------------------------------
# basic put/get
# ----------------------------------------------------------------------


def test_put_and_get(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    b.put("a", b"123")
    b.put("a", b"456")

    assert b.get("a") == b"456"


# ----------------------------------------------------------------------
# KeyError semantics
# ----------------------------------------------------------------------


def test_get_missing_key(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    with pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    with pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    with pytest.raises(KeyError):
        del b["missing"]


# ----------------------------------------------------------------------
# exists / contains
# ----------------------------------------------------------------------


def test_exists_and_contains(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    assert not b.exists("a")
    assert "a" not in b

    b.put("a", b"1")

    assert b.exists("a")
    assert "a" in b


# ----------------------------------------------------------------------
# delete
# ----------------------------------------------------------------------


def test_delete(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    b.put("a", b"123")
    b.delete("a")

    with pytest.raises(KeyError):
        b.get("a")


def test_scan_prefix(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")

    result = sorted(b.scan("a/"))

    assert result == ["a/1", "a/2"]


def test_scan_empty_prefix_returns_all(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    b.put("a", b"x")
    b.put("b", b"x")

    result = sorted(b.scan(""))

    assert result == ["a", "b"]


def test_scan_empty_table(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")
    result = sorted(b.scan(""))
    assert result == []


def test_dict_api(tmp_dir: Path) -> None:
    b = SQLiteBlob(tmp_dir / "blob.db")

    b["a"] = b"123"
    assert b["a"] == b"123"

    del b["a"]

    with pytest.raises(KeyError):
        _ = b["a"]


@pytest.mark.parametrize(
    "name",
    [
        "",
        "1abc",
        "a-b",
        "a b",
        "a;",
        "a,b",
        "a--b",
        "a/b",
        '"abc"',
    ],
)
def test_clean_db_item_invalid(name: str) -> None:
    with pytest.raises(BlobError):
        SQLiteBlob.clean_db_item(name)


@pytest.mark.parametrize(
    "name",
    [
        "a",
        "_a",
        "abc123",
        "ABC",
        "_abc123",
    ],
)
def test_clean_db_item_valid(name: str) -> None:
    assert SQLiteBlob.clean_db_item(name) == name


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


def test_custom_schema(tmp_path: Path) -> None:
    blob = SQLiteBlob(
        tmp_path / "db.sqlite",
        table="objects",
        key_col="name",
        value_col="payload",
    )
    blob.put("k1", b"v1")
    assert blob.get("k1") == b"v1"


def test_reopen(tmp_path: Path) -> None:
    blob = SQLiteBlob(tmp_path / "db.sqlite")
    blob.put("k", b"v")
    blob.close()

    blob = SQLiteBlob(tmp_path / "db.sqlite")
    assert blob.get("k") == b"v"


def test_scan_prefix2(tmp_path: Path) -> None:
    blob = SQLiteBlob(str(tmp_path / "db.sqlite"))

    blob.put("abc", b"")
    blob.put("abcd", b"")
    blob.put("abd", b"")
    blob.put("b", b"")

    assert list(blob.scan("abc")) == [
        "abc",
        "abcd",
    ]


def test_two_instances(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    a = SQLiteBlob(path)
    b = SQLiteBlob(path)
    a.put("k", b"v")
    assert b.get("k") == b"v"
    b.put("k", b"x")
    assert a.get("k") == b"x"


@pytest.mark.parametrize(
    ("table", "key_col", "value_col"),
    [
        ("bad-table", "k", "v"),
        ("bad table", "k", "v"),
        ("123table", "k", "v"),
        ("table;", "k", "v"),
        ("table--x", "k", "v"),
        ('"table"', "k", "v"),
        ("table'", "k", "v"),
        ("table", "k'", "v"),
        ("table", "k", "v'"),
    ],
)
def test_invalid_table_name(
    tmp_path: Path, table: str, key_col: str, value_col: str
) -> None:
    with pytest.raises(BlobError):
        SQLiteBlob(
            str(tmp_path / "db.sqlite"),
            table=table,
            key_col=key_col,
            value_col=value_col,
        )


@pytest.mark.parametrize(
    ("table", "key_col", "value_col"),
    [
        ("blobs", "k", "v"),
        ("t1", "_k", "value1"),
        ("tbl123", "key", "val"),
    ],
)
def test_valid_identifiers(
    tmp_path: Path, table: str, key_col: str, value_col: str
) -> None:
    blob = SQLiteBlob(
        str(tmp_path / "db.sqlite"),
        table=table,
        key_col=key_col,
        value_col=value_col,
    )

    blob.put("x", b"1")
    assert blob.get("x") == b"1"
