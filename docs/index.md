---
template: index.html
hide:
  - navigation
  - toc
hero:
  title: Gufo Blob
  subtitle: Unified blob storage access with predictable semantics
  install_button: Getting Started
  source_button: Source Code
---

[![PyPi version](https://img.shields.io/pypi/v/gufo_blob.svg)](https://pypi.python.org/pypi/gufo_blob/)
![Downloads](https://img.shields.io/pypi/dw/gufo_blob)
![Python Versions](https://img.shields.io/pypi/pyversions/gufo_blob)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
![Build](https://img.shields.io/github/actions/workflow/status/gufolabs/gufo_blob/py-tests.yml?branch=master)
[![codecov](https://codecov.io/gh/gufolabs/gufo_blob/graph/badge.svg?token=WPQTHR6C59)](https://codecov.io/gh/gufolabs/gufo_blob)
![Sponsors](https://img.shields.io/github/sponsors/gufolabs)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff)

---

**Documentation**: [https://docs.gufolabs.com/gufo_blob/](https://docs.gufolabs.com/gufo_blob/)

**Source Code**: [https://github.com/gufolabs/gufo_blob/](https://github.com/gufolabs/gufo_blob/)

Gufo Blob is a lightweight, typed abstraction layer for working with key-based object storage across different backends. It provides a consistent and predictable API for accessing, resolving, and iterating over data regardless of the underlying storage implementation.

## Examples

### Synchronous API

**put/get/delete**

```python
from gufo.blob.sync import open_blob

with open_blob("/var/data") as blob:
    # Store
    blob.put("myproj/k1", b"data")
    # Get
    v = blob.get("myproj/k1")
    # Delete
    blob.delete("myproj/k1")
```

**dict-like API**

```python
from gufo.blob.sync import open_blob

with open_blob("/var/data") as blob:
    # Save
    blob["myproj/k1"] = b"data"
    # Get
    v = blob["myproj/k1"]
    # Delete
    del blob["myproj/k1"]
```

### Asynchronous API

```python
from gufo.blob.aio import open_blob

async def main():
    async with open_blob("/var/data") as blob:
        # Store
        await blob.put("myproj/k1", b"data")
        # Get
        v = await blob.get("myproj/k1")
        # Delete
        await blob.delete("myproj/k1")
```

## Features

- **Sync and async modes** - Provides API for both sync and async modes of operation.
- **Unified blob abstraction** — consistent API for working with different storage backends
- **Backend-agnostic design** — works with local filesystem and pluggable storage implementations
- **Fully typed API** — strict typing for keys, values, and storage contracts
- **Agent-friendly architecture** — explicit interfaces and uniform backend semantics simplify AI-assisted development
- **Simple object model** — intuitive Blob / BlobBase interface with predictable semantics
- **Lazy operations** — resources are initialized and opened only when required
- **Explicit lifecycle control** — optional open() / close() with context manager support
- **Transparent connection handling** — automatic resource management for connected backends
- **Efficient scanning** — fast iteration over stored keys with minimal overhead
- **Key-based access model** — uniform resolution of objects via string keys
- **Error unification** — all runtime issues reduce to `BlobError` and `KeyError`
- **Deterministic behavior** — consistent resolution and iteration order guarantees where applicable
- **Extensible architecture** — easy to add new storage backends and resolvers
- **Designed for composition** — works naturally inside larger systems and pipelines

## On Gufo Stack

This product is a part of [Gufo Stack][Gufo Stack] - the collaborative effort 
led by [Gufo Labs][Gufo Labs]. Our goal is to create a robust and flexible 
set of tools to create network management software and automate 
routine administration tasks.

To do this, we extract the key technologies that have proven themselves 
in the [NOC][NOC] and bring them as separate packages. Then we work on API,
performance tuning, documentation, and testing. The [NOC][NOC] uses the final result
as the external dependencies.

[Gufo Stack][Gufo Stack] makes the [NOC][NOC] better, and this is our primary task. But other products
can benefit from [Gufo Stack][Gufo Stack] too. So we believe that our effort will make 
the other network management products better.

[Gufo Labs]: https://gufolabs.com/
[Gufo Stack]: https://docs.gufolabs.com/
[NOC]: https://getnoc.com/