# ---------------------------------------------------------------------
# Gufo Blob: FTPBlob sync tests
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Third-party modules
import pytest

# Gufo Blob modules
from gufo.blob.error import BlobError
from gufo.blob.sync.ftp import FTPBlob, FTPFeatures

from .helpers.ftpd import FTPInfo

TEST_SCAN_FEATURES = [
    FTPFeatures(),
    FTPFeatures(supports_mlsd=True, supports_mlst=True),
]
TEST_EXISTS_FEATURES = [
    FTPFeatures(),
    FTPFeatures(supports_mlsd=True, supports_mlst=True),
    FTPFeatures(supports_size=True),
]


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
    host, port = FTPBlob._parse_pasv(line)
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
        FTPBlob._parse_pasv(line)


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


# ----------------------------------------------------------------------
# basic put/get
# ----------------------------------------------------------------------


def test_put_and_get(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    assert b.get("a") == b"123"


def test_overwrite(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    b.put("a", b"456")
    assert b.get("a") == b"456"


def test_nested_put(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    items = ["a/b/1", "a/2", "a/b/3", "a/b/c/4"]
    for n, item in enumerate(items):
        b.put(item, chr(n).encode())
    for n, item in enumerate(items):
        assert b.get(item) == chr(n).encode()


def test_get_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        b.get("missing")


def test_delete_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        b.delete("missing")


def test_delitem_missing_key(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    with pytest.raises(KeyError):
        del b["missing"]


@pytest.mark.parametrize("features", TEST_EXISTS_FEATURES)
def test_exists_and_contains(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    assert not b.exists("a")
    assert "a" not in b
    b.put("a", b"1")
    assert b.exists("a")
    assert "a" in b


def test_delete(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b.put("a", b"123")
    b.delete("a")
    with pytest.raises(KeyError):
        b.get("a")


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_prefix(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    b.put("a/1", b"x")
    b.put("a/2", b"x")
    b.put("b/1", b"x")
    result = sorted(b.scan("a/"))
    assert result == ["a/1", "a/2"]


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_empty_prefix_returns_all(
    ftpinfo: FTPInfo, features: FTPFeatures
) -> None:
    b = ftpinfo.blob_with_features(features)
    b.put("a", b"x")
    b.put("b", b"x")
    result = sorted(b.scan(""))
    assert result == ["a", "b"]


@pytest.mark.parametrize("features", TEST_SCAN_FEATURES)
def test_scan_empty_table(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = ftpinfo.blob_with_features(features)
    result = sorted(b.scan(""))
    assert result == []


def test_dict_api(ftpinfo: FTPInfo) -> None:
    b = ftpinfo.blob
    b["a"] = b"123"
    assert b["a"] == b"123"
    del b["a"]
    with pytest.raises(KeyError):
        _ = b["a"]


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
    r = list(FTPBlob.iter_parent_dirs(key))
    assert r == expected


@pytest.mark.parametrize(
    "features",
    [
        FTPFeatures(
            supports_mlsd=False, supports_mlst=False, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=True, supports_mlst=False, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=False, supports_mlst=True, supports_size=False
        ),
        FTPFeatures(
            supports_mlsd=False, supports_mlst=False, supports_size=True
        ),
    ],
)
def test_exists_impl(ftpinfo: FTPInfo, features: FTPFeatures) -> None:
    b = FTPBlob(
        host=ftpinfo.host,
        port=ftpinfo.port,
        user=ftpinfo.user,
        password=ftpinfo.password,
        timeout=1.0,
        features=features,
    )
    key1 = "a/b/c"
    b.put(key1, b"xxx")
    assert b.exists(key1) is True
    assert b.exists("a/b/d") is False
    assert b.exists("a") is False
    assert b.exists("a/b") is False
    assert b.exists("b/c") is False


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
    parsed_name, parsed_is_dir = FTPBlob._parse_mlsd_line(line)
    assert parsed_name == name
    assert parsed_is_dir is is_dir


def test_parse_mlsd_line_decode_error() -> None:
    with pytest.raises(BlobError):
        FTPBlob._parse_mlsd_line(b"\xff")


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
    parsed_name, parsed_is_dir = FTPBlob._parse_list_line(line)
    assert parsed_name == name
    assert parsed_is_dir is is_dir


def test_parse_list_line_decode_error() -> None:
    with pytest.raises(BlobError):
        FTPBlob._parse_list_line(b"-r--r--r-- \xff")
