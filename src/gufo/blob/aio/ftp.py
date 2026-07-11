# ---------------------------------------------------------------------
# Gufo Blob: FTP backend (async, passive mode only)
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""Async FTPBlob implementation."""

# Python modules
from __future__ import annotations

import asyncio
import random
import socket
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

# Gufo Blob modules
from ..common.ftp import (
    DEFAULT_PASSWORD,
    DEFAULT_USER,
    FTP_ACTION_OK,
    FTP_CREATED,
    FTP_LOGIN_OK,
    FTP_NOT_FOUND,
    FTP_OK,
    FTP_PASV,
    FTP_READY,
    FTP_SIZE_OK,
    FTP_STATUS,
    FTP_TRANSFER_ALREADY_OPEN,
    FTP_TRANSFER_DONE,
    FTP_TRANSFER_READY,
    FTP_USER_OK,
    FTPFeatures,
    iter_parent_dirs,
    parse_list_line,
    parse_mlsd_line,
    parse_pasv,
)
from ..error import BlobError
from ..utils import bytes_to_int_range
from .base import BlobBase

RETRY_RANGE = 0.2  # +- 10% of retry timeout
CRLF = b"\r\n"
RECV_SIZE = 65536
MIN_FTP_RESPONSE = 4


@dataclass
class _Conn:
    """Async FTP control connection wrapper."""

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()


class FTPBlob(BlobBase):
    """Async FTP blob backend using native ``asyncio``.

    Stores objects as files on a remote FTP server (passive mode). All
    operations use ``asyncio`` streams and never block the event loop.

    Only passive mode is supported. Active mode (PORT/EPRT), TLS (FTPS),
    and resume operations (REST) are not implemented.

    Args:
        host: FTP server hostname or address.
        port: FTP server port (default 21).
        user: Login username.
        password: Login password.
        root: Root directory prefix on the remote server.
        timeout: Operation and socket connect timeout in seconds.
        retries: Connection retry attempts on failure.
        retry_timeout: Base delay between connection retries.
        features: Optional explicit :class:`FTPFeatures`.  When provided,
            ``FEAT`` won't be probed lazily.
    """

    name = "ftp"

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int = 21,
        user: str = DEFAULT_USER,
        password: str = DEFAULT_PASSWORD,
        root: str = "",
        timeout: float = 30.0,
        retries: int = 3,
        retry_timeout: float = 1.0,
        features: FTPFeatures | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._root = root.strip("/")
        self._timeout = timeout
        self._retries = retries
        self._retry_timeout = retry_timeout
        self._pending_features = features
        self._response_buffer = b""
        self._conn: _Conn | None = None

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """Parse FTP URL and extract parameters for constructor.

        Args:
            url: URL to parse.

        Returns:
            **kwargs for constructor.
        """
        u = urlparse(url)
        if not u.hostname:
            msg = "hostname not set"
            raise BlobError(msg)
        return {
            "host": u.hostname,
            "port": u.port or 21,
            "user": unquote(u.username or DEFAULT_USER),
            "password": unquote(u.password or DEFAULT_PASSWORD),
            "root": u.path.strip("/"),
        }

    async def open(self) -> None:
        """Perform connection routines when necessary.

        Raises:
            BlobError: on error.
        """
        _ = await self.connection  # Force connection

    async def close(self) -> None:
        """Perform cleanup routines when necessary."""
        conn = self._conn
        self._conn = None
        try:
            with suppress(BlobError):
                await self._cmd("QUIT")
        finally:
            if conn is not None:
                await conn.close()

    @property
    async def connection(self) -> _Conn:
        """Get connected reader and writer.

        Returns:
            Connected streams that have passed login.

        Raises:
            BlobError: on error.
        """
        if not self._conn:
            reader, writer = await self._tcp_connect()
            self._conn = _Conn(reader, writer)
            try:
                await self._login()
            except BlobError:
                await self._conn.close()
                self._conn = None
                raise
        return self._conn

    async def _tcp_connect(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Connect to FTP server.

        Returns:
            Connected reader/writer pair.

        Raises:
            BlobError: on error.
        """
        last_error: str = ""
        for _ in range(self._retries):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=self._timeout,
                )
                return reader, writer
            except TimeoutError as e:
                last_error = f"FTP connection timeout: {e}"
            except ConnectionRefusedError as e:
                last_error = f"FTP connection refused: {e}"
            except OSError as e:
                last_error = f"FTP OS error during connect: {e}"
            offset = RETRY_RANGE * (random.random() - 0.5)  # noqa: S311 not a crypto
            await asyncio.sleep(self._retry_timeout * (1.0 + offset))
        msg = f"failed to connect after {self._retries}: {last_error}"
        raise BlobError(msg)

    async def _login(self) -> None:
        """Perform login sequence.

        Raises:
            BlobError: on login failed.
        """
        await self._expect(FTP_READY)
        # Process USER
        code, _ = await self._cmd(f"USER {self._user}")
        if code == FTP_USER_OK:
            code, _ = await self._cmd(f"PASS {self._password}")
        if code != FTP_LOGIN_OK:
            msg = f"LOGIN failed: {code}"
            raise BlobError(msg)
        if self._root:
            code, _ = await self._cmd(f"CWD /{self._root}")
            if code != FTP_ACTION_OK:
                msg = f"CWD /{self._root} failed: {code}"
                raise BlobError(msg)
        # Set binary (image) transfer mode for all subsequent data operations
        code, _ = await self._cmd("TYPE I")
        if code != FTP_OK:
            msg = f"Failed to set binary transfer mode: {code}"
            raise BlobError(msg)

    async def _read_line(self) -> bytes:
        """Read socket or buffer until CRLF.

        Returns:
            Line with stripped CRLF.
        """
        while True:
            line, crlf, rest = self._response_buffer.partition(CRLF)
            if crlf == CRLF:
                self._response_buffer = rest
                return line
            try:
                reader = (await self.connection).reader
                data = await asyncio.wait_for(
                    reader.read(RECV_SIZE), timeout=self._timeout
                )
            except TimeoutError as e:
                msg = "timed out"
                raise BlobError(msg) from e
            except OSError as e:
                msg = f"OS error: {e}"
                raise BlobError(msg) from e
            if not data and reader.at_eof():
                msg = "server closed connection"
                raise BlobError(msg)
            self._response_buffer = (
                self._response_buffer + data if self._response_buffer else data
            )

    async def _read_response(self) -> tuple[int, list[bytes]]:
        """Read a complete FTP server response.

        Supports both single-line and multi-line responses as defined by
        RFC 959. For multi-line responses, reading continues until the
        terminating line with the same reply code followed by a space.

        Returns:
            A tuple containing reply code and list of lines without CRLF.

        Raises:
            BlobError: on read or protocol error.
        """
        lines: list[bytes] = [await self._read_line()]
        first = lines[0]
        if len(first) < MIN_FTP_RESPONSE:
            msg = "response too short"
            raise BlobError(msg)
        code = bytes_to_int_range(first[:3], min_value=0, max_value=999)
        if first[3:4] == b"-":  # multi-line
            while True:
                line = await self._read_line()
                lines.append(line)
                if (
                    len(line) >= MIN_FTP_RESPONSE
                    and line[:3] == first[:3]
                    and line[3:4] == b" "
                ):
                    break
        return code, lines

    async def _cmd(self, cmd: str) -> tuple[int, list[bytes]]:
        """Send an FTP command and read the server response.

        Args:
            cmd: FTP command without the trailing CRLF.

        Returns:
            Tuple of (reply_code, list_of_lines).

        Raises:
            BlobError: on send or protocol error.
        """
        try:
            conn = await self.connection
            conn.writer.write(cmd.encode() + CRLF)
            await asyncio.wait_for(conn.writer.drain(), timeout=self._timeout)
        except TimeoutError as e:
            msg = "timed out during send"
            raise BlobError(msg) from e
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            msg = f"FTP send error: {e}"
            raise BlobError(msg) from e
        return await self._read_response()

    async def _expect(self, code: int) -> None:
        """Read the next FTP response and validate its reply code.

        Args:
            code: Expected FTP reply code.

        Raises:
            BlobError: If the received reply code differs from *code*.
        """
        got, _ = await self._read_response()
        if got != code:
            msg = f"expected {code}, got {got}"
            raise BlobError(msg)

    async def _get_passive_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Enter passive mode and open FTP data connection.

        Returns:
            Data reader/writer pair.

        Raises:
            BlobError: on error.
        """
        code, lines = await self._cmd("PASV")
        if code != FTP_PASV:
            msg = f"PASV failed: {code}"
            raise BlobError(msg)
        host, port = parse_pasv(lines[-1])
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self._timeout,
            )
        except (TimeoutError, ConnectionRefusedError, OSError) as e:
            msg = f"FTP data connection failed: {e}"
            raise BlobError(msg) from e
        return reader, writer

    async def _close_data(self, writer: asyncio.StreamWriter) -> None:
        """Gracefully close FTP data connection.

        Sends a half-close (SHUT_WR) so the server knows the client
        has finished writing before the socket is fully closed. This
        ensures proper 226/CODE response on the control channel for
        STOR operations across all major FTP servers (vsftpd, ProFTPD,
        etc.). For reading data (RETR, LIST, MLSD) the server already
        sends FIN after completing the transfer, so SHUT_WR is best-
        effort cleanup.
        """
        sock = writer.get_extra_info("socket")
        if sock is not None:
            with suppress(OSError):
                sock.shutdown(socket.SHUT_WR)
        try:
            writer.close()
            await writer.wait_closed()
        except OSError:
            pass

    async def _pasv_cmd(self, cmd: str) -> bytes:
        """Execute command and read data from passive connection.

        Args:
            cmd: Command to send on the control channel.

        Returns:
            Received data from the PASV data channel.

        Raises:
            KeyError: If the server reports 550 (not found).
            BlobError: on error.
        """
        d_reader, d_writer = await self._get_passive_connection()
        chunks: list[bytes] = []
        try:
            code, _ = await self._cmd(cmd)
            if code == FTP_NOT_FOUND:
                raise KeyError(cmd.split(" ", 1)[-1])
            if code not in (FTP_TRANSFER_ALREADY_OPEN, FTP_TRANSFER_READY):
                msg = f"unexpected response: {code}"
                raise BlobError(msg)
            # Read data until server closes the connection or times out
            while True:
                try:
                    data = await asyncio.wait_for(
                        d_reader.read(RECV_SIZE), timeout=self._timeout
                    )
                    if data:
                        chunks.append(data)
                    else:
                        break
                except TimeoutError as e:
                    with suppress(BlobError):
                        await self._expect(FTP_TRANSFER_DONE)
                    msg = "timed out"
                    raise BlobError(msg) from e
                except OSError as e:
                    with suppress(BlobError):
                        await self._expect(FTP_TRANSFER_DONE)
                    msg = f"OS error: {e}"
                    raise BlobError(msg) from e
            await self._expect(FTP_TRANSFER_DONE)
        finally:
            await self._close_data(d_writer)
        return b"".join(chunks)

    async def _ensure_parent_dirs(self, key: str) -> None:
        """
        Ensure all key's parent directories are exist.

        Args:
            key: Key to put

        Raises:
            BlobErorr: in case of errors.
        """
        try:
            for d in iter_parent_dirs(key):
                code, _ = await self._cmd(f"MKD {d}")
                if code not in (FTP_CREATED, FTP_NOT_FOUND):
                    msg = f"cannot create {d}: {code}"
                    raise BlobError(msg)
        except TimeoutError as e:
            msg = "timed out"
            raise BlobError(msg) from e
        except OSError as e:
            msg = f"OS Error: {e}"
            raise BlobError(msg) from e

    async def put(self, key: str, data: bytes) -> None:
        """Store binary data under the given key.

        Creates intermediate remote directories automatically via
        ``MKD``.  If the key already exists, its value is overwritten.

        Args:
            key: Object key (remote path).
            data: Binary payload.

        Raises:
            BlobError: On backend or I/O failure.
        """
        await self._ensure_parent_dirs(key)
        _, d_writer = await self._get_passive_connection()
        try:
            code, _ = await self._cmd(f"STOR {key}")
            if code not in (FTP_TRANSFER_ALREADY_OPEN, FTP_TRANSFER_READY):
                msg = f"unexpected response: {code}"
                raise BlobError(msg)
            try:
                d_writer.write(data)
                await asyncio.wait_for(d_writer.drain(), timeout=self._timeout)
            except TimeoutError as e:
                with suppress(BlobError):
                    await self._expect(FTP_TRANSFER_DONE)
                msg = "timed out"
                raise BlobError(msg) from e
            except OSError as e:
                with suppress(BlobError):
                    await self._expect(FTP_TRANSFER_DONE)
                msg = f"OS error: {e}"
                raise BlobError(msg) from e
        finally:
            await self._close_data(d_writer)
        await self._expect(FTP_TRANSFER_DONE)

    async def get(self, key: str) -> bytes:
        """Retrieve data by key.

        Args:
            key: Object key.

        Returns:
            Stored bytes.

        Raises:
            KeyError: If the server reports 550 (file not found).
            BlobError: On backend or I/O failure.
        """
        return await self._pasv_cmd(f"RETR {key}")

    async def delete(self, key: str) -> None:
        """Delete key.

        Args:
            key: Object key.

        Raises:
            KeyError: If the key does not exist.
            BlobError: On backend or I/O failure.
        """
        code, _ = await self._cmd(f"DELE {key}")
        if code == FTP_NOT_FOUND:
            raise KeyError(key)
        if code != FTP_ACTION_OK:
            msg = f"DELE failed: {code}"
            raise BlobError(msg)

    @property
    async def features(self) -> FTPFeatures:
        """Get FTP server features.

        Lazily probed via ``FEAT`` on first access after connection.

        Returns:
            Parsed :class:`FTPFeatures`.
        """
        if self._pending_features is not None:
            return self._pending_features
        code, lines = await self._cmd("FEAT")
        if code == FTP_STATUS:
            # Server supports FEAT -- cache parsed features
            parsed = FTPFeatures.from_feat(lines)
            self._pending_features = parsed
            return parsed
        # Server does not support FEAT -- all features disabled
        self._pending_features = FTPFeatures()
        return self._pending_features

    async def exists(self, key: str) -> bool:
        """Check whether a key exists on the server.

        Uses SIZE first (if supported), then MLST, and falls back to
        scanning via LIST when neither is available.

        Args:
            key: Object key.

        Returns:
            True if the key exists as a file, False otherwise.

        Raises:
            BlobError: On backend or I/O failure.
        """
        features = await self.features
        if features.supports_size:
            code, _ = await self._cmd(f"SIZE {key}")
            if code == FTP_SIZE_OK:
                return True
            if code == FTP_NOT_FOUND:
                return False
        if features.supports_mlst:
            code, lines = await self._cmd(f"MLST {key}")
            if code == FTP_ACTION_OK:
                return any(b"type=file" in line for line in lines)
            if code == FTP_NOT_FOUND:
                return False
        # MLST/SIZE unavailable -- fall back to scan
        async for k in self.scan(key):
            if k == key:
                return True
        return False

    async def _scan(
        self,
        prefix: str,
        cmd: str,
        parser: Callable[[bytes], tuple[str, bool]],
    ) -> AsyncIterator[str]:
        """List remote keys using the given command.

        Recursively walks directories that match the prefix, yielding
        keys for matching file entries.

        Args:
            prefix: Key prefix filter.
            cmd: Command to send (MLSD, LIST).
            parser: Line parser returning (name, is_dir).

        Yields:
            Matching keys under *prefix*.

        Raises:
            BlobError: On connection/protocol error.
        """

        async def list_dir(path: str, rest: list[str]) -> AsyncIterator[str]:
            path = path.rstrip("/")
            try:
                data = await self._pasv_cmd(f"{cmd} {path}" if path else cmd)
            except KeyError:
                return
            for line in data.splitlines():
                name, is_dir = parser(line)
                full_path = f"{path}/{name}" if path else name
                if rest and name == rest[0] and is_dir:
                    async for k in list_dir(full_path, rest[1:]):
                        yield k
                elif not rest and not is_dir:
                    # scan("") -- yield all files at root level
                    yield full_path
                elif rest and name == rest[0] and not is_dir:
                    yield full_path

        parts = [p for p in prefix.split("/") if p]
        async for k in list_dir("", parts):
            yield k

    def scan(self, prefix: str) -> AsyncIterator[str]:
        """Iterate all keys within prefix.

        Uses ``MLSD`` when available, falling back to ``LIST``.

        Args:
            prefix: Prefix to scan.  Empty string scans root.

        Returns:
            Yields matched keys.

        Raises:
            BlobError: On backend or I/O failure.
        """

        async def _async_wrapper() -> AsyncIterator[str]:
            # MLSD is preferred (structured RFC 3659 format)
            features = await self.features
            if features.supports_mlsd:
                async for k in self._scan(prefix, "MLSD", parse_mlsd_line):
                    yield k
            else:
                async for k in self._scan(prefix, "LIST", parse_list_line):
                    yield k

        return _async_wrapper()
