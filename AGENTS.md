# AGENTS — Gufo Blob

## Architecture

Gufo Blob provides synchronous (`gufo.blob.sync`) and asynchronous (`gufo.blob.aio`) API surfaces for key-value blob storage. Each backend implements the flat keyspace model (key string → bytes). URL-based schema routing selects the storage implementation.

### Files

- `error.py` — `BlobError(Exception)`
- `sync/base.py` — abstract `BlobBase`; dict-like protocol (`__getitem__/setitem/delitem/contains`); context manager via inherited `open()`/`close()`. scan returns `Iterable[str]`.
- `aio/base.py` — abstract async `BlobBase`. All methods are `async def`; scan returns `AsyncIterator[str]` (used as `async for`). Context manager: `async with`.
- `sync/memory.py` — in-memory dict backend (`memory://`); thread-safe via `threading.Lock`; `max_objects`/`max_size` hard limits.
- `aio/memory.py` — in-memory backend; event-loop-safe via `asyncio.Lock`; scan snapshots under lock, then iterates snapshot.
- `sync/sqlite.py` — SQLite3 backend (`sqlite://`); WAL journaling, autocommit; lazy connect with double-checked locking and `check_same_thread=False`. Table schema auto-created via `CREATE TABLE IF NOT EXISTS … WITHOUT ROWID`. Custom table/column names validated against `[A-Za-z_][A-Za-z0-9_]*`.
- `aio/sqlite.py` — `AsyncWrapper[SyncSQLiteBlob]`; delegates all ops to background thread pool.
- `sync/file.py` — filesystem backend (`file://` or bare path); auto-creates intermediate directories; rejects absolute keys and escaped paths via `path.resolve().relative_to(root)`.
- `aio/_wrapper.py` — generic async wrapper for sync backends (`to_thread`); `AsyncIterWrapper[T]` snapshot-based async iteration.

### URL routing

`parse_url(url)` extracts schema (everything before first `:`). Default is `"file"`. Each backend registers via `gufo.blob.sync` / `gufo.blob.aio` namespace loader from `gufo-loader`. The classmethod returns kwargs dict for the constructor.

## Dev workflow

```bash
# lint + formatting (ruff auto-fix on write)
pip install -e .[lint]
ruff format src/ tests/
ruff check    src/ tests/
mypy --strict src/

# tests (pytest 9.x, asyncio 1.4.x)
pip install -e .[test]
pytest tests/ -v
pytest tests/ --cov    # branch=false, include="src/*"

# docs
pip install -e .[docs]
mkdocs serve              # preview
mkdocs gh-deploy --strict --force   # deploy
```

## Coding conventions

1. Google docstring (pyproject.toml `[tool.ruff.lint.pydocstyle] convention = "google"`). `get()` describes reading, `delete()` deletion, `put()` writing — never copy between methods.
2. No `Returns: ...` for `-> None` methods. Never document return data in `delete()`.
3. Generator docstrings use `"Yields"` under `Returns:` header (not *"Yelds"*).
4. All backend I/O errors → `BlobError`. Missing keys → `KeyError` via `from e`. No bare `except`/silent `pass`.
5. Import order: stdlib → third-party (gufo-loader) → self (relative import).
6. Line length 79.

## Adding a backend

1. Create `sync/<name>.py` implementing all abstract methods of the parent `BlobBase`. Use lazy connect pattern (`connection` property, double-checked locking) for file-based backends (see `sqlite.py`). For in-memory: use `threading.Lock` or `asyncio.Lock` as appropriate.
2. Implement `parse_url(url: str) -> dict[str, Any]`. On unsupported schemas, raise `BlobError`. Validate identifiers against `[A-Za-z_][A-Za-z0-9_]*` if they become part of SQL/fs paths — reject invalid ones at construction time with `BlobError`.
3. Create `aio/<name>.py` — prefer native async implementation over `AsyncWrapper[SyncBackend]`, use later only when async version is not available. Consider AsyncWrapper uses thread executor.
4. Add tests: at minimum `put/get`, missing key (KeyError), exists/contains, scan prefix, and backend-specific edge cases.

## Dev tooling — run-dev CLI

All lint and test commands **must** run inside the devcontainer:

```bash
./scripts/run-dev ruff check src/ tests/
./scripts/run-dev ruff format --check src/ tests/
./scripts/run-dev mypy src/
./scripts/run-dev pytest -v
./scripts/run-dev pytest --cov --cov-branch --cov-report=xml
```

Direct `pip install`, `pytest`, `ruff`, or `mypy` calls outside the container **will fail** (missing dependencies, wrong Python version, no venv). Always use `run-dev` as the wrapper.

## Constraints

- Version managed in `__init__.py`; pyproject.toml reads it via `{attr = "gufo.blob.__version__"}`.
- `scan(prefix)` uses string range query (`key >= prefix AND key < prefix + chr(0x10FFFF)`) — SQLite backend; simple `startswith()` — memory backend. Empty prefix scans all keys. No glob/regex/delimiter collapsing.
- File sandboxing: keys cannot start with `/` and must not escape the `root` after resolution. Traversal raises `BlobError`.
- Memory limits: enforced via `_check_limits(new_key, new_size)` using projected-state calculation before applying the write. For updates, old value size is subtracted; for inserts, object count and total size are incremented.
