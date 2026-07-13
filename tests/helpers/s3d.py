# ---------------------------------------------------------------------
# Gufo Blob: S3 test fixtures (moto)
# ---------------------------------------------------------------------
# Copyright (C) 2026, Gufo Labs
# ---------------------------------------------------------------------

"""S3-compatible server via moto."""

# Python modules
from __future__ import annotations

import secrets
import socket
import string
import time
from collections.abc import Iterable
from dataclasses import dataclass

# Third-party modules
import boto3
import pytest
from moto.server import ThreadedMotoServer

# Gufo Blob modules
from gufo.blob.common.s3 import S3Info


def _random_string(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@dataclass(frozen=True)
class MotoServerInfo:
    """Moto server info: host, port, access/secret keys."""

    host: str
    port: int
    bucket: str


@pytest.fixture(scope="session")
def s3d() -> Iterable[MotoServerInfo]:
    """Run moto S3 mock server for the entire test session."""
    access_key = "testing"
    secret_key = "testing"

    server = ThreadedMotoServer(port=0, verbose=False)
    server.start()

    # Wait for Tornado to actually bind and accept connections
    def wait_for_server() -> int:
        for _ in range(40):  # up to 10s total
            try:
                sock = socket.create_connection(
                    ("127.0.0.1", server.port or 5555), timeout=0.5
                )
                sock.close()
                return server.port or 5555
            except (OSError, TimeoutError):
                time.sleep(0.25)
        msg = "moto server did not start"
        raise RuntimeError(msg)

    actual_port = wait_for_server()
    bucket_name = _random_string()

    endpoint_url = f"http://127.0.0.1:{actual_port}"
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
    )

    info = MotoServerInfo(
        host="127.0.0.1",
        port=actual_port,
        bucket=bucket_name,
    )
    yield info

    client.delete_bucket(Bucket=bucket_name)
    server.stop()


@pytest.fixture
def s3info(s3d: MotoServerInfo) -> Iterable[S3Info]:
    access_key = "testing"
    secret_key = "testing"
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
    for obj in client.list_objects_v2(Bucket=test_bucket).get("Contents", []):
        client.delete_object(Bucket=test_bucket, Key=obj["Key"])
    client.delete_bucket(Bucket=test_bucket)


@pytest.fixture
def s3info_with_prefix(s3d: MotoServerInfo) -> Iterable[S3Info]:
    access_key = "testing"
    secret_key = "testing"
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
    for obj in client.list_objects_v2(Bucket=test_bucket).get("Contents", []):
        client.delete_object(Bucket=test_bucket, Key=obj["Key"])
    client.delete_bucket(Bucket=test_bucket)
