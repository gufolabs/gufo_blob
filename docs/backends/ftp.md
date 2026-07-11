# FTP Backend

Connects to a remote FTP server in passive mode (PASV) and exposes it as a blob store. Objects are stored as files; the key is used directly as the remote file path relative to the configured root directory. The backend probes `FEAT` on first access and falls back to `LIST` when `MLSD` is unavailable. All sockets use configurable timeouts; initial connection retries include randomized jitter.

## Properties

| Property             | Level                   |
| ---                  | ---                     |
| Data durability      | Host-crash safety       |
| Data sharing         | Network-distributed     |

## Parameters

| Parameter       | Default          | Description                                                             |
| ---             | ---              | ---                                                                     |
| `host`          | *(required)*     | FTP server hostname or IP address.                                      |
| `port`          | `21`             | FTP control port.                                                       |
| `user`          | `"anonymous"`    | Login username (URL-decoded).                                           |
| `password`      | `"anonymous@"`   | Login password (URL-decoded).                                          |
| `root`          | `""`             | Root directory on the remote server; leading and trailing `/` stripped.  |
| `timeout`       | `30.0`           | Socket timeout in seconds for both control and data connections.         |
| `retries`       | `3`              | Number of connection attempts on initial connect.                        |
| `retry_timeout` | `1.0`            | Base delay between retries (±10 % jitter).                              |
| `features`      | `None`           | Explicit `FTPFeatures`. When provided, skips lazy `FEAT` probe.         |

## Behavior

**Login:** Send `USER`, then `PASS` (if 331). If root is configured, `CWD /{root}`. Finish with `TYPE I` to enforce binary transfer mode. On login failure the socket closes and reconnects cleanly on the next access.

**Put:** Creates intermediate remote directories via `MKD` before sending data over the PASV channel. Overwrites existing keys silently.

**Exists:** Checks `SIZE` first if available, then `MLST`. Falls back to scanning the directory when neither is supported. Raises `BlobError` on protocol failures — does not distinguish "file not found" from other errors here.

**Scan (recursive):** Downloads a structured listing via `MLSD` (preferred) or `LIST` (fallback) and recurses into subdirectories that match the prefix. The `LIST` parser expects Unix-style permission bytes — non-Unix servers may produce parse errors.

## Limitations

- Only passive mode is supported. Active mode (`PORT`/`EPRT`), TLS (`FTPS`), and resume (`REST`) are not implemented.
- The `LIST` fallback parser assumes Unix output format (`[-d][rwxs]{9} …`). Non-compliant servers fail on `scan()`.
- Network-dependent — unreachable server, connection reset, or firewall blocking data-port range causes `BlobError`.
- `delete()` raises `KeyError` if the remote file does not exist.

## URL Routing

Schema: `ftp://`. The `parse_url` method extracts host, port (default 21), credentials (URL-decoded, default anonymous), and root path from the standard URL format. Missing hostname raises `BlobError`; `timeout`, `retries`, `retry_timeout`, and `features` must be passed via constructor kwargs as query parameters are not parsed.

## Examples

=== "URL"

    ```text
    ftp://user:pass@ftp.example.com/webroot
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.ftp import FTPBlob

    with FTPBlob("ftp.example.com", user="user", password="pass", root="/webroot") as blob:
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.ftp import AsyncFTPBlob

    async with AsyncFTPBlob("ftp.example.com", user="user", password="pass", root="/webroot") as blob:
        ...
    ```

## Compatibility

FTP backend have been tested against:

* pyftpdlib