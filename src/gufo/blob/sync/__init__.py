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
"""

# Gufo Blob modules
from ..error import BlobError
from .base import BlobBase, open_blob

__all__ = ["BlobBase", "BlobError", "open_blob"]
