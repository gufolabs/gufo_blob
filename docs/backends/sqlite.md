# SQLite Backend

Stores keys and binary values in a persistent SQLite database file. Table schema is created automatically on first connection. Uses WAL journaling and autocommit mode for concurrent host-level access.

## Properties

| Property           | Level          |
| ---                | ---            |
| Data durability    | Host crash     |
| Data sharing       | Host-shared    |

## Parameters

| Parameter      | Default   | Description                                          |
| ---            | ---       | ---                                                  |
| `path`         | *(required)* | SQLite database file path.                              |
| `table`        | `blobs`    | Table name     |
| `key_col`      | `k`       | Column storing keys (TEXT PRIMARY KEY).               |
| `value_col`    | `v`       | Column storing values (BLOB NOT NULL).                |
| `busy_timeout` | `5000`    | SQLite busy retry timeout in milliseconds.             |

## Restrictions

- Database file path is not resolved — stored as-is; use absolute paths for predictable behavior.
- `table`, `key_col`, and `value_col` are validated and invalid identifiers raise `BlobError`.

## Examples

Default settings:

=== "URL"

    ```text
    sqlite:///var/data/blobs.db
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.sqlite import SQLiteBlob
    
    with SQLiteBlob("/var/data/blobs.db") as blob:
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.sqlite import SQLiteBlob
    
    async with SQLiteBlob("/var/data/blobs.db") as blob:
        ...
    ```

Custom table and fields:

=== "URL"

    ```text
    sqlite:///var/data/blobs.db?table=data&key_col=id&value_col=data
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.sqlite import SQLiteBlob
    
    with SQLiteBlob(
        "/var/data/blobs.db",
        table="data",
        key_col="id",
        value_col="data"
    ) as blob:
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.sqlite import SQLiteBlob
    
    async with SQLiteBlob(
        "/var/data/blobs.db",
        table="data",
        key_col="id",
        value_col="data"
    ) as blob:
        ...
    ```