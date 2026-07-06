# ---------------------------------------------------------------------
# Gufo Blob: Asynchronous SQLite backend
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""SQLiteBlob implementation."""

# Python modules
from pathlib import Path

# Gufo Blob modules
from ..sync.sqlite import (
    BUSY_TIMEOUT,
    DEFAULT_KEY,
    DEFAULT_TABLE,
    DEFAULT_VALUE,
)
from ..sync.sqlite import SQLiteBlob as SyncSQLiteBlob
from ._wrapper import AsyncWrapper


class SQLiteBlob(AsyncWrapper[SyncSQLiteBlob]):
    """
    Async SQLite backend for Gufo Blob.

    URL format:
        sqlite:///path/to/db.sqlite

    Options:
        table: table name (default: blobs)
        key: key column name (default: k)
        value: value column name (default: v)
        busy_timeout: Busy timeout (ms)

    !!! note

        This implementation uses threads to achieve non-blocking behaviour.
    """

    name = "sqlite"
    inner = SyncSQLiteBlob

    def __init__(
        self,
        path: str | Path,
        table: str = DEFAULT_TABLE,
        key_col: str = DEFAULT_KEY,
        value_col: str = DEFAULT_VALUE,
        busy_timeout: int = BUSY_TIMEOUT,
    ) -> None:
        super().__init__(
            SyncSQLiteBlob(
                path=path,
                table=table,
                key_col=key_col,
                value_col=value_col,
                busy_timeout=busy_timeout,
            )
        )
