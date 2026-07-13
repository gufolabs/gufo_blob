# ---------------------------------------------------------------------
# Gufo Blob: Sync interface
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""
Synchronous backends.

Available out-of-the-box:

* [MemoryBlob][gufo.blob.sync.memory.MemoryBlob]: Stores data in the
    process' memory
* [FileBlob][gufo.blob.sync.file.FileBlob]: Host filesystem.
* [SQLiteBlob][gufo.blob.sync.sqlite.SQLiteBlob]: SQLite database.
* [FTPBlob][gufo.blob.sync.ftp.FTPBlob]: FTP server.
* [S3Blob][gufo.blob.sync.s3.S3Blob]: S3-compatible storage.
"""

# Gufo Blob modules
from ..error import BlobError
from .base import BlobBase, open_blob

__all__ = ["BlobBase", "BlobError", "open_blob"]
