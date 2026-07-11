# ---------------------------------------------------------------------
# Gufo Blob: FTP definitions and utilities
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------
"""Common FTP definitions and utilities."""

# Python modules
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# Gufo Blob modules
from ..error import BlobError
from ..utils import bytes_to_octet

# FTP reply codes
FTP_TRANSFER_READY = 125
FTP_TRANSFER_ALREADY_OPEN = 150
FTP_OK = 200
FTP_STATUS = 211
FTP_SIZE_OK = 213
FTP_READY = 220
FTP_TRANSFER_DONE = 226
FTP_PASV = 227
FTP_LOGIN_OK = 230
FTP_ACTION_OK = 250
FTP_CREATED = 257
FTP_USER_OK = 331
FTP_UNAVAILABLE = 421
FTP_NOT_FOUND = 550

rx_pasv = re.compile(rb"\((\d+,\d+,\d+,\d+,\d+,\d+)\)")
rx_unix_perm = re.compile(rb"[\-d]([\-r][\-w][\-x]){3}")


@dataclass
class FTPFeatures:
    """
    FTP Server features.

    Attributes:
        supports_mlsd: MLSD command is supported.
        supports_mlst: MLST command is supported.
        supports_size: SIZE command is supported.
    """

    supports_mlsd: bool = False
    supports_mlst: bool = False
    supports_size: bool = False

    @classmethod
    def from_feat(cls, feat: list[bytes]) -> FTPFeatures:
        """
        Parse FEAT response.

        Args:
            feat: Feat response from FTP server

        Returns:
            Parsed FTPFeatures.
        """
        features = cls()
        for line in feat:
            parts = line.split()
            match parts[0].upper():
                case b"MLSD":
                    features.supports_mlst = True  # assumed with MLSD
                    features.supports_mlsd = True
                case b"SIZE":
                    features.supports_size = True
                case _:
                    pass
        return features


def parse_pasv(line: bytes) -> tuple[str, int]:
    """
    Parse PASV response line and extract host/port.

    Args:
        line: Raw PASV response line.

    Returns:
        Tuple of (host, port).

    Raises:
        BlobError: If response format is invalid.
    """
    match = rx_pasv.search(line)
    if not match:
        msg = f"Invalid PASV response: {line!r}"
        raise BlobError(msg)
    h1, h2, h3, h4, p1, p2 = [
        bytes_to_octet(x) for x in match.group(1).split(b",")
    ]
    host = f"{h1}.{h2}.{h3}.{h4}"
    port = (p1 << 8) + p2
    return host, port


def parse_list_line(line: bytes) -> tuple[str, bool]:
    """
    Parse one line of LIST output.

    Args:
        line: input line.

    Returns:
        Tuple of (file name, is directory)

    Raises:
        BlobError: on unparsable line.
    """
    if not rx_unix_perm.match(line):
        msg = f"unrecognized format: {line!r}"
        raise BlobError(msg)
    try:
        name = line.split()[-1].decode()
    except UnicodeDecodeError as e:
        msg = f"failed to decode: {line!r}"
        raise BlobError(msg) from e
    is_dir = line.startswith(b"d")
    return name, is_dir


def parse_mlsd_line(line: bytes) -> tuple[str, bool]:
    """
    Parse one line of MLSD output.

    Args:
        line: input line.

    Returns:
        Tuple of (file name, is directory)

    Raises:
        BlobError: on unparsable line.
    """
    parts = line.split(b";")
    try:
        name = parts[-1].lstrip(b" ").rstrip(b"/").decode()
    except UnicodeDecodeError as e:
        msg = f"failed to decode: {parts[-1]!r}"
        raise BlobError(msg) from e
    is_dir = any(p == b"type=dir" for p in parts[:-1])
    return name, is_dir


def iter_parent_dirs(key: str) -> Iterable[str]:
    """
    Iterate all full paths to the parent.

    Args:
        key: current key.

    Returns:
        All full paths to the parent directories.
    """
    parts = key.strip("/").split("/")
    current: list[str] = []
    for part in parts[:-1]:
        current.append(part)
        yield "/".join(current)
