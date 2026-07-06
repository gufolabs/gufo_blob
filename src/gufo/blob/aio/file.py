# ---------------------------------------------------------------------
# Gufo Blob: Asynchronous file backend
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""FileBlob implementation."""

# Gufo Blob modules
from ..sync.file import FileBlob as SyncFileBlob
from ._wrapper import AsyncWrapper


class FileBlob(AsyncWrapper[SyncFileBlob]):
    """
    Filesystem-backed blob store.

    Stores binary objects on local filesystem under a fixed root
    directory.

    The API exposes a flat keyspace model. There are no directories
    in the logical model, only keys.

    All operations are sandboxed to prevent escaping the root directory
    via path traversal or absolute paths.

    !!! note

        This implementation uses threads to achieve non-blocking behaviour.
    """

    name = "file"
    inner = SyncFileBlob

    def __init__(self, root: str) -> None:
        super().__init__(SyncFileBlob(root))
