# ---------------------------------------------------------------------
# Gufo Blob: Various utilities
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""Various utilities."""

# Gufo Blob modules
from .error import BlobError


def bytes_to_int(x: bytes) -> int:
    """
    Convert string representation to integer value.

    Args:
        x: string representation

    Returns:
        Converted integer.

    Raises:
        BlobError: on invalid value
    """
    try:
        return int(x)
    except ValueError as e:
        msg = f"Expecting integer: {x!r}"
        raise BlobError(msg) from e


def bytes_to_int_range(
    x: bytes, min_value: int | None = None, max_value: int | None = None
) -> int:
    """
    Convert string representation to integer in range.

    Args:
        x: string representation.
        min_value: Optional minimum value.
        max_value: Optional max value.

    Returns:
        converted integer.

    Raises:
        BlobError: on error.
    """
    n = bytes_to_int(x)
    if min_value is not None and n < min_value:
        msg = f"too low. expected {min_value} or greater"
        raise BlobError(msg)
    if max_value is not None and n > max_value:
        msg = f"too large. expected {max_value} or less."
        raise BlobError(msg)
    return n


MAX_OCTET = 255


def bytes_to_octet(x: bytes) -> int:
    """
    Convert string representation to octet value.

    Arga:
        x: string representation

    Returns:
        integer octet.

    Raises:
        BlobError: on invalid value
    """
    n = bytes_to_int(x)
    if n < 0 or n > MAX_OCTET:
        msg = f"Octet is out of bounds: {n}"
        raise BlobError(msg)
    return n
