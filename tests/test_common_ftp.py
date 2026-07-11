# ---------------------------------------------------------------------
# Gufo Blob: FTP commons test
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.common.ftp import (
    FTPFeatures,
    iter_parent_dirs,
    parse_list_line,
    parse_mlsd_line,
    parse_pasv,
)
from gufo.blob.error import BlobError


@pytest.mark.parametrize(
    ("lines", "supports_mlsd", "supports_mlst", "supports_size"),
    [
        ([], False, False, False),
        (
            [
                b" EPRT",
                b" EPSV",
                b" MDTM",
                b" MLSD type*;perm*;size*;modify*;unique*;",
                b" MFMT",
                b" REST STREAM",
                b" SIZE",
                b" UTF8",
            ],
            True,
            True,
            True,
        ),
        (
            [
                b" EPRT",
                b" EPSV",
                b" MDTM",
                b" MLSD type*;perm*;size*;modify*;unique*;",
                b"",
                b" MFMT",
                b" REST STREAM",
                b" SIZE",
                b" UTF8",
            ],
            True,
            True,
            True,
        ),
        ([b" MLSD"], True, True, False),
        ([b" mlsd type*;", b" mlst size*"], True, True, False),
    ],
)
def test_from_feat(
    lines: list[bytes],
    supports_mlsd: bool,
    supports_mlst: bool,
    supports_size: bool,
) -> None:
    feat = FTPFeatures.from_feat(lines)
    assert feat.supports_mlsd is supports_mlsd
    assert feat.supports_mlst is supports_mlst
    assert feat.supports_size is supports_size


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            b"227 Entering Passive Mode (192,168,0,1,195,44)",
            ("192.168.0.1", 195 * 256 + 44),
        ),
        (
            b"227 Passive Mode (10,0,0,5,1,20)",
            ("10.0.0.5", 1 * 256 + 20),
        ),
    ],
)
def test_parse_pasv_ok(line: bytes, expected: tuple[str, int]) -> None:
    host, port = parse_pasv(line)
    assert (host, port) == expected


@pytest.mark.parametrize(
    "line",
    [
        b"227 broken response",
        b"227 (not,enough,numbers)",
        b"",
        b"invalid",
        b"227 Entering Passive Mode (1,2,3)",  # too short
        b"227 Passive Mode (256,0,0,5,1,20)",  # too big integer
        b"227 Passive Mode (10,256,0,5,1,20)",  # too big integer
        b"227 Passive Mode (10,0,256,5,1,20)",  # too big integer
        b"227 Passive Mode (10,0,0,256,1,20)",  # too big integer
        b"227 Passive Mode (10,0,0,5,256,20)",  # too big integer
        b"227 Passive Mode (10,0,0,5,1,256)",  # too big integer
    ],
)
def test_parse_pasv_error(line: bytes) -> None:
    with pytest.raises(BlobError):
        parse_pasv(line)


@pytest.mark.parametrize(
    ("line", "name", "is_dir"),
    [
        (
            b"modify=20260709062230;perm=radfwMT;size=1;type=file;unique=4bg55665f4; 1",
            "1",
            False,
        ),
        (
            b"modify=20260709062230;perm=radfwMT;size=1;type=dir;unique=4bg55665f4; 1",
            "1",
            True,
        ),
        (
            b"modify=20260709062230;perm=radfwMT;size=1;unique=4bg55665f4; 1",
            "1",
            False,
        ),
    ],
)
def test_parse_mlsd_line(line: bytes, name: str, is_dir: bool) -> None:
    parsed_name, parsed_is_dir = parse_mlsd_line(line)
    assert parsed_name == name
    assert parsed_is_dir is is_dir


def test_parse_mlsd_line_decode_error() -> None:
    with pytest.raises(BlobError):
        parse_mlsd_line(b"\xff")


@pytest.mark.parametrize(
    ("line", "name", "is_dir"),
    [
        (
            b"-rw-r--r--   1 root     root            1 Jul 09 06:41 1",
            "1",
            False,
        ),
        (
            b"drw-r--r--   1 root     root            1 Jul 09 06:41 1",
            "1",
            True,
        ),
    ],
)
def test_parse_list_line(line: bytes, name: str, is_dir: bool) -> None:
    parsed_name, parsed_is_dir = parse_list_line(line)
    assert parsed_name == name
    assert parsed_is_dir is is_dir


def test_parse_list_line_decode_error() -> None:
    with pytest.raises(BlobError):
        parse_list_line(b"-r--r--r-- \xff")


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("", []),
        ("aaa", []),
        ("aaa/bbb", ["aaa"]),
        ("aaa/bbb/ccc", ["aaa", "aaa/bbb"]),
        ("aaa/bbb/ccc/ddd", ["aaa", "aaa/bbb", "aaa/bbb/ccc"]),
    ],
)
def test_iter_parent_dir(key: str, expected: list[str]) -> None:
    r = list(iter_parent_dirs(key))
    assert r == expected
