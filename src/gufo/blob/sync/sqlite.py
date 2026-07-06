# ---------------------------------------------------------------------
# Gufo Blob: SQLite sync backend
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""SQLiteBlob implementation."""

# Python modules
from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path
from threading import Lock
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

# Gufo Blob modules
from ..error import BlobError
from .base import BlobBase

DEFAULT_TABLE = "blobs"
DEFAULT_KEY = "k"
DEFAULT_VALUE = "v"
BUSY_TIMEOUT = 5000

rx_db_item = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteBlob(BlobBase):
    """
    Sync SQLite backend for Gufo Blob.

    URL format:
        sqlite:///path/to/db.sqlite

    Options:
        table: table name (default: blobs)
        key: key column name (default: k)
        value: value column name (default: v)
        busy_timeout: Busy timeout (ms)
    """

    name = "sqlite"

    def __init__(
        self,
        path: str | Path,
        table: str = DEFAULT_TABLE,
        key_col: str = DEFAULT_KEY,
        value_col: str = DEFAULT_VALUE,
        busy_timeout: int = BUSY_TIMEOUT,
    ) -> None:
        self._path = Path(path)
        self._table = self.clean_db_item(table)
        self._key_col = self.clean_db_item(key_col)
        self._value_col = self.clean_db_item(value_col)
        self._busy_timeout = busy_timeout
        self._conn_lock = Lock()  # guard connection creation
        self._conn: sqlite3.Connection | None = None

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """
        Parse URL and extract parameters for constructor.

        Args:
            url: URL to parse.

        Returns:
            `**kwargs` for constructor.
        """
        p = urlparse(url)
        if p.scheme != "sqlite":
            msg = f"Invalid URL scheme: {p.scheme}"
            raise BlobError(msg)
        qs = parse_qs(p.query)
        return {
            "path": p.path,
            "table": qs.get("table", [DEFAULT_TABLE])[0],
            "key_col": qs.get("key", [DEFAULT_KEY])[0],
            "value_col": qs.get("value", [DEFAULT_VALUE])[0],
        }

    @property
    def path(self) -> Path:
        """Get database path."""
        return self._path

    @property
    def table(self) -> str:
        """Get table name."""
        return self._table

    @property
    def key_col(self) -> str:
        """Get key column name."""
        return self._key_col

    @property
    def value_col(self) -> str:
        """Get value column name."""
        return self._value_col

    @staticmethod
    def clean_db_item(name: str) -> str:
        """
        Check database field or table name.

        Args:
            name: database object name.

        Returns:
            database object name if valid.

        Raises:
            BlobError: on invalid name
        """
        if not rx_db_item.fullmatch(name):
            msg = f"Invalid database identifier: {name!r}"
            raise BlobError(msg)
        return name

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Get SQLite connection.

        Connect and initialize database schema when necessary.
        """
        if self._conn:  # hot path
            return self._conn
        with self._conn_lock:
            # Must recheck under the lock
            if self._conn:
                return self._conn
            self._conn = sqlite3.connect(
                self._path,
                isolation_level=None,  # autocommit mode
                check_same_thread=False,
            )
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute(f"PRAGMA busy_timeout={self._busy_timeout};")
            for sql in self.iter_init_sql():
                self._conn.execute(sql)
            return self._conn

    def open(self) -> None:
        """Explicitly open connection."""
        _ = self.connection  # force connect

    def close(self) -> None:
        """Close connection."""
        with self._conn_lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def iter_init_sql(self) -> Iterable[str]:
        """Iterate database initialization queries."""
        yield f"""
        CREATE TABLE IF NOT EXISTS {self._table} (
            {self._key_col} TEXT PRIMARY KEY,
            {self._value_col} BLOB NOT NULL
        ) WITHOUT ROWID
        """

    def put(self, key: str, data: bytes) -> None:
        """
        Store binary data under the given key.

        If the key already exists, its value is overwritten.

        Args:
            key: Object key.
            data: Binary payload.

        Raises:
            BlobError: On backend or I/O failure.
        """
        q = f"""
        INSERT INTO {self._table} ({self._key_col}, {self._value_col})
        VALUES (?, ?)
        ON CONFLICT({self._key_col}) DO UPDATE SET
            {self._value_col}=excluded.{self._value_col}
        """  # noqa: S608
        self.connection.execute(q, (key, data))

    def get(self, key: str) -> bytes:
        """
        Retrieve data by key.

        Args:
            key: Object key.

        Raises:
            BlobError: On backend or I/O failure.
        """
        q = f"""
        SELECT {self._value_col}
        FROM {self._table}
        WHERE {self._key_col}=?
        """  # noqa: S608
        cursor = self.connection.execute(q, (key,))
        row = cursor.fetchone()
        if row is None:
            raise KeyError(key)
        return cast(bytes, row[0])

    def delete(self, key: str) -> None:
        """
        Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """
        q = f"""
        DELETE FROM {self._table}
        WHERE {self._key_col}=?
        """  # noqa: S608
        cursor = self.connection.execute(q, (key,))
        if cursor.rowcount == 0:
            raise KeyError(key)

    def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the blob store.

        Args:
            key: Object key.

        Returns:
            True if the key exists, False otherwise.

        Raises:
            BlobError: On backend or I/O failure.
        """
        q = f"""
        SELECT 1
        FROM {self._table}
        WHERE {self._key_col}=?
        LIMIT 1
        """  # noqa: S608
        return self.connection.execute(q, (key,)).fetchone() is not None

    def scan(self, prefix: str) -> Iterator[str]:
        """
        Iterate all keys within prefix.

        Args:
            prefix: Prefix to scan.

        Returns:
            Yields matched keys.

        Raises:
            BlobError: On backend or I/O failure.
        """
        q = f"""
        SELECT {self._key_col}
        FROM {self._table}
        WHERE {self._key_col} >= ?
          AND {self._key_col} < ?
        ORDER BY {self._key_col}
        """  # noqa: S608
        upper = prefix + chr(0x10FFFF)
        cursor = self.connection.execute(q, (prefix, upper))
        for (k,) in cursor:
            yield k
