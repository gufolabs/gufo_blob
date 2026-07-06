# ---------------------------------------------------------------------
# Gufo Blob
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""
Gufo Blob - Unified blob storage access with predictable semantics.

Gufo Blob is a lightweight, typed abstraction layer for working
with key-based object storage across different backends.
It provides a consistent and predictable API for accessing,
resolving, and iterating over data regardless of the underlying
storage implementation.

* [sync backends][gufo.blob.sync]: Synchronous mode.
* [async backends][gufo.blob.aio]: Async mode.
"""

__version__: str = "0.1.0"
__all__ = ["__version__"]
