---
hide:
    - navigation
---
## Getting Started with Gufo Blob

### What is "Gufo Blob"?
Gufo Blob is a lightweight Python library for working with blob storage systems and file-like abstractions.

It provides a unified interface for interacting with different backends (local filesystem, S3-like object storage, and others) while keeping the core API simple and predictable.

### Which Python versions are supported?
Python 3.10 and later. The test matrix covers Python 3.10 through 3.14. There are no external runtime dependencies beyond the standard library.

### How is Gufo Blob different from fsspec?

Unlike fsspec, Gufo Blob is:
- more minimal and opinionated
- less abstract and easier to reason about
- designed with explicit lifecycle control in mind

fsspec aims for maximum coverage of storage systems, while Gufo Blob focuses on simplicity, security, and control.

### Can I use it for caching?

Yes — Gufo Blob can be used as a caching layer for blob-like data.

However, it is important to understand that caching is not a primary responsibility of the library.

You can absolutely build cache-like patterns on top of it, but:

- cache eviction (TTL-based or size-based) is not provided out of the box
- there is no built-in guarantee of automatic cleanup
- any caching logic must be implemented externally

In practice, this means Gufo Blob can store cached artifacts, but cache lifecycle management (TTL, LRU, size limits, etc.) is the responsibility of the application layer, not the library itself.

### Does it support versioning?

Versioning depends entirely on the backend.

Gufo Blob itself does not impose a unified versioning model — it delegates this capability to the underlying storage implementation.

- Some backends may provide native versioning support (e.g., object storage systems with versioned objects)
- Others may behave as simple key-value stores without history
- In many cases, only the latest value is accessible

From the library’s perspective, versioning is therefore optional and backend-specific, not a core abstraction.

### Do I need to manually open connections?

Usually no.

Gufo Blob supports lazy initialization, so connections are opened automatically when needed:

```python
with open_blob(...) as blob:
    blob.put("key", b"data")
```

Or even:

```python
blob.put("key", b"data")
```

if the backend handles connection lifecycle internally.

### How does the context manager work?

Gufo Blob objects support the standard Python context manager protocol:

- `open()` — initialize backend resources
- `close()` — release resources
- `__enter__` / `__exit__` — automatic lifecycle handling

This ensures safe cleanup when used inside with blocks.

### What happens if I don’t call close()?

If `close()` is not called explicitly:

- connections may remain open
- resources may not be released immediately
- some backends may leak file handles or sessions

Recommended usage:

- prefer `with ...`
- or explicitly call `close()`

### Does Gufo Blob support lazy connection opening?

Yes.

Connections are typically established only when the first operation occurs (`put`, `get`, `scan`, etc.), or `open` called explicitly or via context manager, reducing overhead during object creation.

### What is scan()?
`scan()` iterates over keys in the storage backend.

Important characteristics:
- may return empty or partial results depending on backend
- can be lazy/streaming
- performance depends on storage implementation
- semantics may differ between filesystem and object storage backends

### Why does scan() sometimes return unexpected keys?

Because backend systems differ:

- local filesystem - real paths
- S3-like systems - prefixes / virtual keys
- custom backends - may introduce synthetic namespaces

Gufo Blob does not fully normalize semantics to preserve backend behavior transparency.

### Can I implement custom backends?
Yes.

Gufo Blob is designed to be extended with custom storage backends by implementing the required interface:

- open/close lifecycle
- put/get operations
- optional scan support

### How are errors handled?
All storage-related errors are normalized into a small, predictable set of exceptions:

- `BlobError` — the base exception for all backend and storage-level issues
- `KeyError` — raised when a requested key does not exist

This design keeps error handling consistent across different backends while avoiding backend-specific exception leakage into user code.


### Is Gufo Blob tightly coupled to the Gufo ecosystem?
It can be used standalone, but:

- it is optimized for Gufo projects
- some design decisions assume integration with larger Gufo systems
- backend choice may reflect internal ecosystem needs

## Support and License

### What license is Gufo Blob released under?

Gufo Blob is released under the [3-clause BSD License](https://opensource.org/licenses/BSD-3-Clause). You are free to use it in commercial, open-source, or private projects.

### Where can I get help or report a bug?

Please open a [GitHub Issue](https://github.com/gufolabs/gufo_blob/issues) for bugs, feature requests, or architectural questions. Discussions are welcome as well.

### Can I support the Gufo Stack project financially?

Yes. You can support our work via [GitHub Sponsors](https://github.com/sponsors/gufolabs) or [Buy Me a Coffee](https://www.buymeacoffee.com/dvolodin). Your contributions directly fund continued research and maintenance of the Gufo Stack components.

## About Gufo

### What does "Gufo" mean?

*Gufo* means *the Owl* in Italian.

### Why the owls?

We love owls — and the viable parts of our technologies were proven at a project literally named "the Owl" before becoming independent open-source components.

### What is "Gufo Stack"?

We've extracted core components behind the [NOC](https://getnoc.com/) network management platform and released them as independent packages, available under the terms of the 3-clause BSD license. Our software shares common code quality standards and is battle-proven under high load across large-scale ISP deployments. We hope our key components will help engineers build reliable networks and robust network management software.

### What is "Gufo Labs"?

[Gufo Labs](https://gufolabs.com/) is the italian company specializing in network and IT consulting, and in software research for communications infrastructure.