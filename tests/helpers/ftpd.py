# ---------------------------------------------------------------------
# Gufo Blob: ftpd fixture
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

# Python modules
from __future__ import annotations

import logging
import secrets
import shutil
import socket
import string
import tempfile
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

# Third-party modules
import pytest
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# Gufo Blob modules
from gufo.blob.sync.ftp import FTPBlob, FTPFeatures


@dataclass
class FTPInfo:
    """
    FTP server information.

    Attributes:
        host: server host.
        port: server port.
        local_root: Local representation of the server's root directory.
        user: username.
        password: user password.
    """

    host: str
    port: int
    local_root: Path
    user: str
    password: str

    @cached_property
    def blob(self) -> FTPBlob:
        """Get or create cached FTPBlob instance."""
        return FTPBlob(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            timeout=1.0,
        )

    def blob_with_features(self, features: FTPFeatures) -> FTPBlob:
        """Create blob with given features."""
        return FTPBlob(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            timeout=1.0,
            features=features,
        )

    def clone(self) -> FTPInfo:
        """Clone content."""
        return FTPInfo(
            host=self.host,
            port=self.port,
            local_root=self.local_root,
            user=self.user,
            password=self.password,
        )


def _random_string(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@pytest.fixture(scope="session")
def ftpd() -> Iterable[FTPInfo]:
    """
    Run temporary FTP server.

    Returns:
        FTP connection parameters.
    """

    def connect_socket() -> None:
        for _ in range(5):
            try:
                return socket.create_connection((host, port), timeout=0.5)
            except TimeoutError:
                time.sleep(0.5)
        msg = "failed to connect"
        raise TimeoutError(msg)

    def wait_for_ready() -> None:
        sock = connect_socket()
        buf = b""
        while True:
            data = sock.recv(4096)
            if not data:
                msg = "Server resets connection"
                raise RuntimeError(msg)
            buf += data
            if len(buf) < 4:
                continue
            if buf.startswith(b"220 "):
                return
            msg = "invalid ftp negotiation: {b!r}"
            raise RuntimeError(msg)

    with tempfile.TemporaryDirectory(prefix="ftpd-") as root:
        logger = logging.getLogger("pyftpdlib")
        logger.setLevel(logging.DEBUG)
        user = _random_string()
        password = _random_string()
        authorizer = DummyAuthorizer()
        authorizer.add_user(
            user,
            password,
            root,
            perm="elradfmwMT",
        )
        handler = type(
            "TestFTPHandler",
            (FTPHandler,),
            {"authorizer": authorizer},
        )

        server = FTPServer(
            ("127.0.0.1", 0),
            handler,
        )
        host, port = server.socket.getsockname()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"blocking": True, "timeout": 3.0, "worker_processes": 1},
            daemon=True,
        )
        thread.start()
        # Wait for server to actually start accepting connections
        wait_for_ready()
        yield FTPInfo(
            host=host,
            port=port,
            local_root=Path(root),
            user=user,
            password=password,
        )
        server.close_all()
        thread.join(timeout=1)


@pytest.fixture
def ftpinfo(ftpd: FTPInfo) -> Iterable[FTPInfo]:
    """Provide isolated FTP environment for a single test."""
    info = ftpd.clone()
    yield info
    # Clean up data
    for path in info.local_root.iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
