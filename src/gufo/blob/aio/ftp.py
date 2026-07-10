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
from collections.abc import AsyncIterator
from contextlib import suppress
from functools import cached_property
from typing import Any
from urllib.parse import unquote, urlparse

# Gufo Blob modules
from ..common.ftp import (
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
    parse_list_line,
    parse_mlsd_line,
    parse_pasv,
)
from ..error import BlobError
from ..utils import bytes_to_int_range
from .base import BlobBase

DEFAULT_USER = "anonymous"
DEFAULT_PASSWORD = "anonymous@"  # noqa: S105
RETRY_RANGE = 0.2  # +- 10 % of retry timeout
CRLF = b"\r\n"
RECV_SIZE = 65536
MIN_FTP_RESPONSE = 4


class AsyncFTPBlob(BlobBase):
    """Async FTP blob backend using native `asyncio`.

    Stores objects as files on a remote FTP server (passive mode).
    All operations use ``asyncio`` streams — never blocks the event loop.

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
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._response_buffer = b""

    @classmethod
    def parse_url(cls, url: str) -> dict[str, Any]:
        """Parse an FTP URL into constructor kwargs.

        Args:
            url: ``ftp://[user:pass@]host[:port]/path``.

        Returns:
            Keyword arguments for :class:`AsyncFTPBlob(**kwargs)`.

        Raises:
            BlobError: If the hostname is missing from the URL.
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
        """Establish FTP connection and authenticate.

        Raises:
            BlobError: On connection or authentication failure.
        """
        await self._connect_and_login()

    async def close(self) -> None:
        """Send QUIT and close the control connection."""
        if self._writer is None:
            return
        writer = self._writer
        self._writer = None
        self._reader = None
        try:
            with suppress(BlobError):
                await self._cmd("QUIT")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except OSError:
                pass

    async def _connect_and_login(self) -> None:
        """Open TCP stream and complete login sequence."""
        if self._writer is not None:
            return  # already connected
        conn = await self._tcp_connect()
        reader, writer = conn
        self._reader = reader
        self._writer = writer
        try:
            await self._login()
        except BlobError:
            self._clear_transport()
            raise

    def _clear_transport(self) -> None:
        """Abandon current transport without waiting."""
        if self._writer is not None:
            w = self._writer
            self._writer = None
            self._reader = None
            with suppress(OSError):
                w.close()

    async def _tcp_connect(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Establish TCP connection to the FTP server with retries.

        Returns:
            ``(reader, writer)`` pair for control channel.

        Raises:
            BlobError: After exhausting all retry attempts.
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
            offset = RETRY_RANGE * (random.random() - 0.5)  # noqa: S311
            await asyncio.sleep(self._retry_timeout * (1.0 + offset))
        msg = f"failed to connect after {self._retries}: {last_error}"
        raise BlobError(msg)

    async def _login(self) -> None:
        """Perform USER/PASS login and configure the session."""
        await self._expect(FTP_READY)
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
        # Set binary transfer mode for all subsequent data operations
        code, _ = await self._cmd("TYPE I")
        if code != FTP_OK:
            msg = f"Failed to set binary transfer mode: {code}"
            raise BlobError(msg)

    async def _read_line(self) -> bytes:
        """
        Read socket or buffer until CRLF.

        Returns:
            Line with stripped CRLF.
        """
        if self._reader is None:
            msg = "not connected"
            raise BlobError(msg)
        while True:
            line, crlf, rest = self._response_buffer.partition(CRLF)
            if crlf == CRLF:
                self._response_buffer = rest
                return line
            try:
                data = await asyncio.wait_for(
                    self._reader.read(RECV_SIZE), timeout=self._timeout
                )
            except TimeoutError as e:
                msg = "timed out"
                raise BlobError(msg) from e
            except OSError as e:
                msg = f"OS error: {e}"
                raise BlobError(msg) from e
            if not data and self._reader.at_eof():
                msg = "server closed connection"
                raise BlobError(msg)
            self._response_buffer = (
                self._response_buffer + data if self._response_buffer else data
            )

    async def _read_response(self) -> tuple[int, list[bytes]]:
        """Read a complete FTP server response.

        Handles both single-line and multi-line replies per RFC 959.

        Returns:
            Tuple of (reply_code, list_of_lines_without_crlf).

        Raises:
            BlobError: On connection close or malformed response.
        """
        lines: list[bytes] = [await self._read_line()]
        first = lines[0]
        if len(first) < MIN_FTP_RESPONSE:
            msg = "response too short"
            raise BlobError(msg)
        code = bytes_to_int_range(first[:3], min_value=0, max_value=999)
        if first[3:4] == b"-":
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
        """Send *cmd* on the control connection and read the reply.

        Args:
            cmd: FTP command string (trailing CRLF added automatically).

        Returns:
            ``(reply_code, lines)`` tuple.

        Raises:
            BlobError: On socket or protocol error.
        """
        writer = self._writer
        if writer is None:
            msg = "not connected"
            raise BlobError(msg)
        try:
            writer.write(cmd.encode() + CRLF)
            await asyncio.wait_for(writer.drain(), timeout=self._timeout)
        except TimeoutError as e:
            msg = "timed out during send"
            raise BlobError(msg) from e
        except OSError as e:
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
        """Enter PASV mode and open the data connection.

        Returns:
            ``(reader, writer)`` pair for the data channel.

        Raises:
            BlobError: If PASV negotiation or data connect fails.
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
        except TimeoutError as e:
            msg = f"FTP data connection failed: {e}"
            raise BlobError(msg) from e
        except OSError as e:
            msg = f"FTP data connection failed: {e}"
            raise BlobError(msg) from e
        return reader, writer

    async def _drain_data(
        self,
        d_reader: asyncio.StreamReader,
        d_writer: asyncio.StreamWriter,
    ) -> bytes:
        """Read all data from the PASV channel and expect 226.

        Returns:
            All bytes received on the data channel.

        Raises:
            BlobError: On timeout or network error.
        """
        chunks: list[bytes] = []
        try:
            while not d_reader.at_eof():
                data = await asyncio.wait_for(
                    d_reader.read(RECV_SIZE), timeout=self._timeout
                )
                if not data:
                    break
                chunks.append(data)
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
        return b"".join(chunks)

    async def _close_data_connection(
        self,
        d_writer: asyncio.StreamWriter,
    ) -> None:
        """Gracefully close the data connection writer."""
        try:
            d_writer.close()
            await d_writer.wait_closed()
        except OSError:
            pass

    # ---- Blob API ----------------------------------------------------

    async def put(self, key: str, data: bytes) -> None:
        """Store binary data under *key*.

        Creates intermediate remote directories automatically.  If the
        key already exists, the value is overwritten.

        Args:
            key: Object key (remote file path).
            data: Binary payload to persist.

        Raises:
            BlobError: On I/O or protocol error.
        """
        _, d_writer = await self._get_passive_connection()
        try:
            for parent in _iter_parent_dirs(key):
                code, _ = await self._cmd(f"MKD {parent}")
                if code not in (FTP_CREATED, FTP_NOT_FOUND):
                    msg = f"cannot create directory: {code}"
                    raise BlobError(msg)
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
            await self._close_data_connection(d_writer)
        await self._expect(FTP_TRANSFER_DONE)

    async def get(self, key: str) -> bytes:
        """Retrieve the full binary payload for *key*.

        Args:
            key: Object key (remote file path).

        Returns:
            The stored bytes.

        Raises:
            KeyError: If the server reports ``550`` (file not found).
            BlobError: On connection or protocol error.
        """
        d_reader, d_writer = await self._get_passive_connection()
        try:
            code, _ = await self._cmd(f"RETR {key}")
            if code == FTP_NOT_FOUND:
                raise KeyError(key)
            if code not in (FTP_TRANSFER_ALREADY_OPEN, FTP_TRANSFER_READY):
                msg = f"unexpected response: {code}"
                raise BlobError(msg)
            return await self._drain_data(d_reader, d_writer)
        finally:
            await self._close_data_connection(d_writer)

    async def delete(self, key: str) -> None:
        """Delete the object at *key*.

        Args:
            key: Object key to remove.

        Raises:
            KeyError: If the server reports ``550`` (not found).
            BlobError: On connection or protocol error.
        """
        code, _ = await self._cmd(f"DELE {key}")
        if code == FTP_NOT_FOUND:
            raise KeyError(key)
        if code != FTP_ACTION_OK:
            msg = f"DELE failed: {code}"
            raise BlobError(msg)

    async def exists(self, key: str) -> bool:
        """Check whether *key* exists on the server.

        Queries ``SIZE`` first (if supported), then ``MLST``, then
        falls back to scanning with ``LIST`` (or ``MLSD``).

        Args:
            key: Object key to check.

        Returns:
            ``True`` if the key exists as a file, else ``False``.

        Raises:
            BlobError: On connection or protocol error.
        """
        if self.features.supports_size:
            code, _ = await self._cmd(f"SIZE {key}")
            if code == FTP_SIZE_OK:
                return True
            if code == FTP_NOT_FOUND:
                return False

        if self.features.supports_mlst:
            code, lines = await self._cmd(f"MLST {key}")
            if code == FTP_ACTION_OK:
                return any(b"type=file" in line for line in lines)
            if code == FTP_NOT_FOUND:
                return False

        # Fallback: scan for the key
        async for k in self.scan(key):
            if k == key:
                return True
        return False

    @cached_property
    def features(self) -> FTPFeatures:
        """Server capabilities (lazy ``FEAT`` probe)."""
        if self._pending_features is not None:
            return self._pending_features
        # NOTE: cached_property is sync; this only works after open()
        loop = asyncio.get_event_loop()
        code, lines = loop.run_until_complete(self._cmd("FEAT"))
        if code == FTP_STATUS:
            return FTPFeatures.from_feat(lines)
        return FTPFeatures()

    def scan(self, prefix: str) -> AsyncIterator[str]:
        """Yield all keys under *prefix* (recursive directory walk).

        Uses ``MLSD`` when available, falling back to ``LIST``.

        Args:
            prefix: Key prefix filter.  Empty string scans root.

        Yields:
            Matching object keys as strings.

        Raises:
            BlobError: On connection or protocol error.
        """
        return self._scan_recursive("", prefix)

    async def _scan_recursive(
        self,
        path: str,
        prefix: str,
    ) -> AsyncIterator[str]:
        """Recursively walk the remote directory tree.

        Args:
            path: Current remote path (empty string = root).
            prefix: Remaining key prefix to match against entries.

        Yields:
            Matching file paths as strings.
        """
        parts = [p for p in prefix.split("/") if p]
        try:
            data = await self._get_listing(path)
        except KeyError:
            return  # directory does not exist

        for line in data.splitlines():
            name, is_dir = _parse_line(line, self.features.supports_mlsd)
            full = f"{path}/{name}" if path else name

            if parts and name == parts[0] and is_dir:
                async for k in self._scan_recursive(full, "/".join(parts[1:])):
                    yield k
            elif (parts and name == parts[0] and not is_dir) or (
                not parts and not is_dir
            ):
                yield full

    async def _get_listing(self, path: str) -> bytes:
        """Retrieve directory listing via MLSD or LIST.

        Args:
            path: Remote directory (empty string = root).

        Returns:
            Raw listing data as bytes.

        Raises:
            KeyError: If the server reports the path does not exist.
            BlobError: On transfer failure.
        """
        cmd_name = "MLSD" if self.features.supports_mlsd else "LIST"
        ftp_cmd = f"{cmd_name} {path}" if path else cmd_name

        d_reader, d_writer = await self._get_passive_connection()
        try:
            code, _ = await self._cmd(ftp_cmd)
            if code == FTP_NOT_FOUND:
                raise KeyError(path)
            if code not in (FTP_TRANSFER_ALREADY_OPEN, FTP_TRANSFER_READY):
                msg = f"unexpected response: {code}"
                raise BlobError(msg)
            return await self._drain_data(d_reader, d_writer)
        finally:
            await self._close_data_connection(d_writer)


# ---- Module-level helpers (no instance needed) ----------------------


def _iter_parent_dirs(key: str) -> list[str]:
    """Return parent directory paths from root to immediate parent.

    Example::

        >>> list(_iter_parent_dirs("a/b/c.txt"))  # doctest: +SKIP
        ["a", "a/b"]

    Args:
        key: Remote file path.

    Returns:
        List of ancestor directories in top-down order.
    """
    parts = key.strip("/").split("/")
    current: list[str] = []
    result: list[str] = []
    for part in parts[:-1]:
        current.append(part)
        result.append("/".join(current))
    return result


def _parse_line(line: bytes, use_mlsd: bool) -> tuple[str, bool]:
    """Dispatch to the appropriate parser based on MLSD support."""
    if use_mlsd:
        return parse_mlsd_line(line)
    return parse_list_line(line)
