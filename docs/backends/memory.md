# Memory Backend

Stores data in process-local dictionary, protected by `threading.Lock`. Fastest backend; provides no persistence or cross-process sharing guarantees.

## Properties

| Property           | Level            |
| ---                | ---              |
| Data durability    | Process lifetime |
| Data sharing       | Process-local    |

## Parameters

| Parameter  | Default | Description                                                         |
| ---        | ---     | ---                                                                 |
| `max_objects` | `None` | Maximum number of keys. Raises `BlobError` on overflow.           |
| `max_size`     | `None` | Maximum total size of all values in bytes. Does not count key or Python memory overhead. Raises `BlobError` on overflow. |

## Examples

### Unrestricted storage

=== "URL"

    ```text
    memory:///
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.memory import MemoryBlob
    
    with MemoryBlob() as blob:
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.memory import MemoryBlob
    
    async with MemoryBlob() as blob:
        ...
    ```

### Limited to 1000 keys or 100_000 bytes

=== "URL"

    ```text
    memory:///?max_objects=1000&max_size=100000
    ```

=== "Sync"

    ```python
    from gufo.blob.sync.memory import MemoryBlob
    
    with MemoryBlob(max_objects=1000, max_size=100000):
        ...
    ```

=== "Async"

    ```python
    from gufo.blob.aio.memory import MemoryBlob
    
    async with MemoryBlob(max_objects=1000, max_size=100000):
        ...
    ```
