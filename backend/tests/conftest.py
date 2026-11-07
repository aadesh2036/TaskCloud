"""Shared fixtures. Nothing here can reach AWS: moto intercepts every boto3 call."""

import json
import uuid

import boto3
import pytest
from moto import mock_aws
from shared.attachments import get_attachments
from shared.store import get_store

TABLE = "taskcloud-tasks"
BUCKET = "taskcloud-attachments-test-ap-south-1"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Fake credentials and a fresh data folder for every test."""
    for name, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "ap-south-1",
        "AWS_REGION": "ap-south-1",
        "TABLE_NAME": TABLE,
        "ATTACHMENTS_BUCKET": BUCKET,
        "TASKCLOUD_DATA_DIR": str(tmp_path / "data"),
        # Importing local/server.py sets this to local for the whole process, so pin it per test.
        "TASKCLOUD_STORE": "dynamodb",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    get_store.cache_clear()
    get_attachments.cache_clear()
    yield
    get_store.cache_clear()
    get_attachments.cache_clear()


def create_table():
    boto3.client("dynamodb", region_name="ap-south-1").create_table(
        TableName=TABLE,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "taskId", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "taskId", "AttributeType": "S"},
        ],
    )


def create_bucket():
    s3 = boto3.client("s3", region_name="ap-south-1")
    s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    return s3


@pytest.fixture
def aws():
    with mock_aws():
        create_table()
        create_bucket()
        yield


@pytest.fixture(params=["dynamodb", "local"])
def backend(request, monkeypatch):
    """Run a test against both store backends, to prove they behave the same."""
    monkeypatch.setenv("TASKCLOUD_STORE", request.param)
    if request.param == "dynamodb":
        with mock_aws():
            create_table()
            create_bucket()
            yield request.param
    else:
        yield request.param


def api_event(route_key, user="user-a", body=None, task_id=None):
    """Build an HTTP API payload 2.0 event, as API Gateway would after checking the JWT."""
    event = {
        "version": "2.0",
        "routeKey": route_key,
        "requestContext": {"authorizer": {"jwt": {"claims": {"sub": user}}}} if user else {},
        "pathParameters": {"id": task_id} if task_id else None,
        "isBase64Encoded": False,
    }
    if body is not None:
        event["body"] = body if isinstance(body, str) else json.dumps(body)
    return event


def body_of(response):
    return json.loads(response["body"]) if response.get("body") else None


def new_id():
    return str(uuid.uuid4())


