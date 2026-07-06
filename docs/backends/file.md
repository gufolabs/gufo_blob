# File Backend

Stores binary objects on the local filesystem beneath a single root directory. Every key is resolved to a file; intermediate directories are created automatically. Keys follow a flat keyspace model — no virtual directories in the API. Path traversal is prevented by resolving keys against an absolute `root`.

## Properties

| Property           | Level          |
| ---                | ---            |
| Data durability    | Host crash     |
| Data sharing       | Host-shared    |

## Limitations

- Keys must not start with `/` (absolute paths rejected).
- Resolved path must remain inside the `root`; attempts to escape raise `BlobError`.
- No internal locking; concurrent access relies on filesystem-level atomicity of overwrite.

## Examples

=== "URL"

    ```text
    /var/data
    ```

    Bare path defaults to `file://` schema:

    ```text
    file:///tmp/blob-store
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.file import FileBlob
    
    with FileBlob("/var/data") as blob:
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.file import FileBlob
    
    async with FileBlob("/var/data") as blob:
        ...
    ```
