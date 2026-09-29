---
hide:
    - navigation
---
# Installation

Install with the pip

```bash
$ pip install gufo_blob
```

The S3 backend requires the optional HTTP dependency. Install it with the `http` extra:

```bash
$ pip install "gufo_blob[http]"
```

See [S3 Backend](backends/s3.md) for backend-specific setup and configuration.

## Checking the Installation

To check the installation just import the module

```python
from gufo.blob import __version__
```

## Upgrading

To upgrade existing Gufo Blob installation use pip

```bash
$ pip install --upgrade gufo_blob
```

## Uninstalling

To uninstall Gufo Blob use pip

```bash
$ pip uninstall gufo_blob
```
