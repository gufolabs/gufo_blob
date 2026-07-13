# ---------------------------------------------------------------------
# Gufo Blob: Test configurations
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
import tempfile
from collections.abc import Iterable
from pathlib import Path

# Third-party modules
import pytest

# helpers — auto-imported for pytest fixture discovery
from .helpers.ftpd import ftpd, ftpinfo  # noqa: F401
from .helpers.s3d import s3d, s3info  # noqa: F401


@pytest.fixture
def tmp_dir() -> Iterable[Path]:
    """Create a fresh temporary directory for each test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
