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


@pytest.fixture
def tmp_dir() -> Iterable[Path]:
    """
    Create a fresh temporary directory for each test.

    The directory is automatically removed after test completion.
    """
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
