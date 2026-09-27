# ---------------------------------------------------------------------
# Gufo Blob: S3 test fixtures (moto)
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""S3-compatible server via moto."""

# Python modules
from __future__ import annotations

import secrets
import string
from collections.abc import Iterable
from dataclasses import dataclass

# Third-party modules
import boto3
import pytest
from moto.server import ThreadedMotoServer

# Gufo Blob modules
from gufo.blob.common.s3 import S3Info


def _random_string(length: int = 16) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@dataclass(frozen=True)
class MotoServerInfo:
    """Moto server connection info."""

    host: str
    port: int


@pytest.fixture(scope="session")
def s3d() -> Iterable[MotoServerInfo]:
    """Run moto S3 mock server for the entire test session."""
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    try:
        host, port = server.get_host_and_port()
        yield MotoServerInfo(host=host, port=port)
    finally:
        server.stop()


@pytest.fixture
def s3info(s3d: MotoServerInfo) -> Iterable[S3Info]:
    access_key = "testing"
    secret_key = "testing"  # noqa: S105
    endpoint_url = f"http://{s3d.host}:{s3d.port}"

    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
    )

    test_bucket = _random_string()
    client.create_bucket(Bucket=test_bucket)

    info = S3Info(
        host=s3d.host,
        port=s3d.port,
        bucket=test_bucket,
        access_key=access_key,
        secret_key=secret_key,
    )
    yield info

    # Clean up all objects and delete the test bucket
    pages = client.get_paginator("list_objects_v2").paginate(
        Bucket=test_bucket
    )
    keys = [obj["Key"] for page in pages for obj in page.get("Contents", [])]
    for key in keys:
        client.delete_object(Bucket=test_bucket, Key=key)
    client.delete_bucket(Bucket=test_bucket)


@pytest.fixture
def s3info_with_prefix(s3d: MotoServerInfo) -> Iterable[S3Info]:
    access_key = "testing"
    secret_key = "testing"  # noqa: S105
    endpoint_url = f"http://{s3d.host}:{s3d.port}"

    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
    )

    test_bucket = _random_string()
    client.create_bucket(Bucket=test_bucket)

    info = S3Info(
        host=s3d.host,
        port=s3d.port,
        bucket=test_bucket,
        prefix="test-prefix",
        access_key=access_key,
        secret_key=secret_key,
    )
    yield info

    # Clean up all objects and delete the test bucket
    pages = client.get_paginator("list_objects_v2").paginate(
        Bucket=test_bucket
    )
    keys = [obj["Key"] for page in pages for obj in page.get("Contents", [])]
    for key in keys:
        client.delete_object(Bucket=test_bucket, Key=key)
    client.delete_bucket(Bucket=test_bucket)
