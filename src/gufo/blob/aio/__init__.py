# ---------------------------------------------------------------------
# Gufo Blob: Async interface
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""
Async backends.

Available out-of-the-box:

* [MemoryBlob][gufo.blob.aio.memory.MemoryBlob]: Stores data in the
    process' memory
* [FileBlob][gufo.blob.aio.file.FileBlob]: Host filesystem.
* [SQLiteBlob][gufo.blob.aio.sqlite.SQLiteBlob]: SQLite database.
* [FTPBlob][gufo.blob.aio.ftp.FTPBlob]: FTP server.

"""

from ..error import BlobError
from .base import BlobBase, open_blob

__all__ = ["BlobBase", "BlobError", "open_blob"]
