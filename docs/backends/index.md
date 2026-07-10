# Gufo Blob Backends

Gufo Blob provides several built-in backends, available in both synchronous and asynchronous modes. All synchronous backends are thread-safe, and asynchronous backends are safe for concurrent async access.

## Built-in backends
Backends out of the box:

| Backend | Storage layer |
| --- | --- |
| `memory` | In-process memory |
| `file` | Local filesystem |
| `sqlite` | SQLite database |

## Data durability

Backends may provide different levels of data durability (persistence across failures). Ordered from weakest to strongest guarantees:

1. **Process lifetime** - data available in process lifetime.
2. **Process crash safety** — data survives process restart (in-memory persistence beyond runtime is not guaranteed otherwise)
3. **Host crash safety** — data survives operating system or host restart
4. **Distributed durability (replication)** — data is replicated across multiple storage nodes and survives node failure

## Data sharing

Backends may also differ in the scope of data visibility and sharing. Ordered from narrowest to widest:

1. **Process-local** — data is visible only within a single process.
2. **Host-shared** — data is accessible across multiple processes on the same machine.
3. **Network-distributed** — data is accessible across multiple hosts over a network.

## Backend comparison

| Backend | Data<br>durability | Data<br>sharing |
| --- | --- | --- |
| `memory` | Process lifetime | Process-local |
| `file` | Host crash safety | Host-shared |
| `sqlite` | Host-crash safety [^1] | Host-shared |
| `ftp` | Host-crash safety [^1] | Network-distributed |

## Further reading

See appropriate backend documentation for implementation details.

* [memory](memory.md)
* [file](file.md)
* [sqlite](sqlite.md)
* [ftp](ftp.md)

[^1]: Distributed file systems can increase durability.