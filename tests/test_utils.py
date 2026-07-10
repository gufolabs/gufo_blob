# ---------------------------------------------------------------------
# Gufo Blob: Utils tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.error import BlobError
from gufo.blob.utils import bytes_to_int, bytes_to_int_range, bytes_to_octet

# ----------------------------------------------------------------------
# bytes_to_int
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(b"0", 0), (b"42", 42), (b"-1", -1), (b"9999", 9999)],
)
def test_bytes_to_int_valid(value: bytes, expected: int) -> None:
    assert bytes_to_int(value) == expected


@pytest.mark.parametrize("value", [b"", b"abc", b"12.34"])
def test_bytes_to_int_invalid(value: bytes) -> None:
    with pytest.raises(BlobError):
        bytes_to_int(value)


# ----------------------------------------------------------------------
# bytes_to_octet
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(b"0", 0), (b"128", 128), (b"255", 255)],
)
def test_bytes_to_octet_valid(value: bytes, expected: int) -> None:
    assert bytes_to_octet(value) == expected


@pytest.mark.parametrize("value", [b"-1", b"256", b"abc"])
def test_bytes_to_octet_invalid(value: bytes) -> None:
    with pytest.raises(BlobError):
        bytes_to_octet(value)


# ----------------------------------------------------------------------
# bytes_to_int_range
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "min_value", "max_value", "expected"),
    [
        (b"50", None, None, 50),
        (b"0", 0, 100, 0),
        (b"50", 0, 100, 50),
        (b"100", 0, 100, 100),
        (b"-5", -10, None, -5),
        (b"95", None, 100, 95),
    ],
)
def test_bytes_to_int_range_valid(
    value: bytes,
    min_value: int | None,
    max_value: int | None,
    expected: int,
) -> None:
    assert bytes_to_int_range(value, min_value, max_value) == expected


@pytest.mark.parametrize(
    ("value", "min_value", "max_value"),
    [
        (b"-11", -10, None),
        (b"101", None, 100),
        (b"-11", -10, 100),
        (b"101", -10, 100),
        (b"abc", None, None),
    ],
)
def test_bytes_to_int_range_invalid(
    value: bytes, min_value: int | None, max_value: int | None
) -> None:
    with pytest.raises(BlobError):
        bytes_to_int_range(value, min_value, max_value)
