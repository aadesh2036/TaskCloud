"""Runs the real local server on a free port and points the smoke test at it."""

import threading

import pytest
import server as local_server
import smoke_test
from shared.attachments import get_attachments
from shared.store import get_store


@pytest.fixture
def running_server(monkeypatch):
    monkeypatch.setenv("TASKCLOUD_STORE", "local")
    monkeypatch.delenv("PLANNER_MODE", raising=False)
    server = local_server.create_server(port=0)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("TASKCLOUD_LOCAL_BASE_URL", base_url)
    get_store.cache_clear()
    get_attachments.cache_clear()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield base_url
    server.shutdown()
    server.server_close()


def test_smoke_suite_passes(running_server):
    assert smoke_test.run(running_server) == []


def test_smoke_test_leaves_no_tasks(running_server):
    smoke_test.run(running_server)
    assert get_store().list_tasks("local-user")[0] == []


def test_server_binds_to_loopback_only():
    server = local_server.create_server(port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_bedrock_mode_needs_model_id(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "bedrock")
    monkeypatch.delenv("MODEL_ID", raising=False)
    with pytest.raises(SystemExit, match="MODEL_ID"):
        local_server.build_planner_kwargs()


def test_unknown_planner_mode_is_refused(monkeypatch):
    monkeypatch.setenv("PLANNER_MODE", "magic")
    with pytest.raises(SystemExit, match="stub or bedrock"):
        local_server.build_planner_kwargs()
