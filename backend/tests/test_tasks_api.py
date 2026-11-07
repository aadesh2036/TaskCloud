"""Every test using the backend fixture runs against both DynamoDB (moto) and the JSON file."""

import base64
import json
from datetime import UTC

import boto3
import pytest
from conftest import BUCKET, api_event, body_of, new_id
from functions.attachment_indexer.handler import lambda_handler as indexer
from functions.tasks_api.handler import lambda_handler as handler
from shared.store import get_store

VALID = {"title": "Finish lab record", "dueDate": "2026-11-10", "priority": "high", "estMinutes": 45}


def create(user="user-a", **overrides):
    response = handler(api_event("POST /tasks", user, {**VALID, **overrides}), None)
    assert response["statusCode"] == 201, response
    return body_of(response)


def s3_event(key):
    return {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": key}}}]}


def test_missing_claims_is_401(backend):
    response = handler(api_event("GET /tasks", user=None), None)
    assert response["statusCode"] == 401
    assert body_of(response)["error"] == "Unauthorized"


def test_unknown_route_is_404(backend):
    assert handler(api_event("GET /nope"), None)["statusCode"] == 404


def test_create_sets_server_fields(backend):
    task = create()
    assert task["userId"] == "user-a"
    assert task["source"] == "manual"
    assert task["status"] == "todo"
    assert task["createdAt"].endswith("Z")
    assert "completedAt" not in task


def test_create_cannot_choose_user_or_source(backend):
    for extra in ({"userId": "victim"}, {"source": "agent"}, {"taskId": new_id()}):
        response = handler(api_event("POST /tasks", body={**VALID, **extra}), None)
        assert response["statusCode"] == 400
    assert body_of(handler(api_event("GET /tasks", "victim"), None))["tasks"] == []


@pytest.mark.parametrize("raw", ["{not json", "[1,2]", '"text"'])
def test_bad_json_is_400(backend, raw):
    response = handler(api_event("POST /tasks", body=raw), None)
    assert response["statusCode"] == 400
    assert set(body_of(response)) == {"error", "message"}


def test_base64_body(backend):
    event = api_event("POST /tasks")
    event["body"] = base64.b64encode(json.dumps(VALID).encode()).decode()
    event["isBase64Encoded"] = True
    assert handler(event, None)["statusCode"] == 201


def test_list_returns_only_own_tasks_with_plain_numbers(backend):
    mine = create()
    create(user="user-b")
    response = handler(api_event("GET /tasks"), None)
    payload = body_of(response)
    assert [t["taskId"] for t in payload["tasks"]] == [mine["taskId"]]
    assert payload["truncated"] is False
    assert payload["tasks"][0]["estMinutes"] == 45
    assert isinstance(payload["tasks"][0]["estMinutes"], int)


def test_patch_updates_allowed_fields(backend):
    task = create()
    response = handler(api_event("PATCH /tasks/{id}", body={"title": "New", "priority": "low"}, task_id=task["taskId"]), None)
    assert response["statusCode"] == 200
    updated = body_of(response)
    assert updated["title"] == "New" and updated["priority"] == "low" and updated["dueDate"] == VALID["dueDate"]


def test_patch_rejects_other_fields(backend):
    task = create()
    for body in ({"source": "agent"}, {"userId": "x"}, {"attachmentKey": "a/b/c"}, {}):
        assert handler(api_event("PATCH /tasks/{id}", body=body, task_id=task["taskId"]), None)["statusCode"] == 400


def test_patch_missing_task_is_404_without_creating_it(backend):
    task_id = new_id()
    response = handler(api_event("PATCH /tasks/{id}", body={"title": "x"}, task_id=task_id), None)
    assert response["statusCode"] == 404
    assert get_store().get_task("user-a", task_id) is None


def test_status_controls_completed_at(backend):
    task = create()
    patch = lambda status: body_of(  # noqa: E731
        handler(api_event("PATCH /tasks/{id}", body={"status": status}, task_id=task["taskId"]), None)
    )
    done = patch("done")
    assert done["status"] == "done" and done["completedAt"]
    assert "completedAt" not in patch("todo")


def test_completing_twice_keeps_first_time(backend, monkeypatch):
    from datetime import datetime

    import functions.tasks_api.handler as module

    task = create()
    patch = api_event("PATCH /tasks/{id}", body={"status": "done"}, task_id=task["taskId"])
    monkeypatch.setattr(module, "now_utc", lambda: datetime(2026, 11, 5, tzinfo=UTC))
    first = body_of(handler(patch, None))["completedAt"]
    monkeypatch.setattr(module, "now_utc", lambda: datetime(2026, 11, 7, tzinfo=UTC))
    assert body_of(handler(patch, None))["completedAt"] == first == "2026-11-05T00:00:00Z"


def test_title_patch_keeps_completed_at(backend):
    task = create()
    handler(api_event("PATCH /tasks/{id}", body={"status": "done"}, task_id=task["taskId"]), None)
    updated = body_of(handler(api_event("PATCH /tasks/{id}", body={"title": "x"}, task_id=task["taskId"]), None))
    assert updated["completedAt"]


@pytest.mark.parametrize(
    "route, body",
    [
        ("PATCH /tasks/{id}", {"title": "hacked"}),
        ("DELETE /tasks/{id}", None),
        ("POST /tasks/{id}/attachment-url", {"filename": "a.pdf"}),
        ("GET /tasks/{id}/attachment-url", None),
    ],
)
def test_other_users_task_is_404(backend, route, body):
    task = create(user="user-b")
    response = handler(api_event(route, "user-a", body, task["taskId"]), None)
    assert response["statusCode"] == 404
    assert get_store().get_task("user-b", task["taskId"])["title"] == VALID["title"]


@pytest.mark.parametrize(
    "route, body",
    [
        ("PATCH /tasks/{id}", {"title": "x"}),
        ("DELETE /tasks/{id}", None),
        ("POST /tasks/{id}/attachment-url", {"filename": "a.pdf"}),
        ("GET /tasks/{id}/attachment-url", None),
    ],
)
def test_bad_task_id_is_400(backend, route, body):
    assert handler(api_event(route, body=body, task_id="not-a-uuid"), None)["statusCode"] == 400


def test_delete(backend):
    task = create()
    response = handler(api_event("DELETE /tasks/{id}", task_id=task["taskId"]), None)
    assert response["statusCode"] == 204 and "body" not in response
    assert handler(api_event("DELETE /tasks/{id}", task_id=task["taskId"]), None)["statusCode"] == 404


def test_progress_route(backend):
    task = create()
    create()
    handler(api_event("PATCH /tasks/{id}", body={"status": "done"}, task_id=task["taskId"]), None)
    result = body_of(handler(api_event("GET /progress"), None))
    assert (result["total"], result["done"], result["todo"], result["completedToday"], result["streakDays"]) == (
        2, 1, 1, 1, 1,
    )
    assert len(result["last7Days"]) == 7 and result["last7Days"][-1]["done"] == 1


def test_upload_url_shape(backend):
    task = create()
    response = handler(
        api_event("POST /tasks/{id}/attachment-url", body={"filename": "my notes.pdf", "size": 100}, task_id=task["taskId"]),
        None,
    )
    assert response["statusCode"] == 200
    payload = body_of(response)
    assert payload["key"] == f"user-a/{task['taskId']}/my_notes.pdf"
    assert payload["fields"]["key"] == payload["key"]
    assert payload["expiresIn"] == 300 and payload["maxBytes"] == 10 * 1024 * 1024


def test_upload_url_size_limits(backend):
    task = create()
    event = lambda size: api_event(  # noqa: E731
        "POST /tasks/{id}/attachment-url", body={"filename": "a.pdf", "size": size}, task_id=task["taskId"]
    )
    assert handler(event(10 * 1024 * 1024), None)["statusCode"] == 200
    assert handler(event(10 * 1024 * 1024 + 1), None)["statusCode"] == 413
    for bad in (0, -1, "big", True):
        assert handler(event(bad), None)["statusCode"] == 400


def test_upload_url_requires_filename(backend):
    task = create()
    assert handler(api_event("POST /tasks/{id}/attachment-url", body={}, task_id=task["taskId"]), None)["statusCode"] == 400


def test_second_attachment_is_409(backend):
    task = create()
    key = f"user-a/{task['taskId']}/a.pdf"
    indexer(s3_event(key), None)
    response = handler(api_event("POST /tasks/{id}/attachment-url", body={"filename": "b.pdf"}, task_id=task["taskId"]), None)
    assert response["statusCode"] == 409


def test_download_needs_an_attachment(backend):
    task = create()
    assert handler(api_event("GET /tasks/{id}/attachment-url", task_id=task["taskId"]), None)["statusCode"] == 404


def test_unexpected_error_is_500_without_details(backend, monkeypatch):
    import functions.tasks_api.handler as module

    def boom():
        raise RuntimeError("secret table detail")

    monkeypatch.setattr(module, "get_store", boom)
    response = handler(api_event("GET /tasks"), None)
    assert response["statusCode"] == 500
    assert "secret" not in response["body"]
    assert body_of(response)["error"] == "InternalError"


# --- Indexer ---


def test_indexer_sets_attachment(backend):
    task = create()
    key = f"user-a/{task['taskId']}/a.pdf"
    assert indexer(s3_event(key), None) == {"indexed": 1, "ignored": 0}
    assert get_store().get_task("user-a", task["taskId"])["attachmentKey"] == key


def test_indexer_decodes_key_with_plus_and_percent(backend):
    task = create()
    assert indexer(s3_event(f"user-a/{task['taskId']}/my+notes%281%29.pdf"), None)["indexed"] == 1
    stored = get_store().get_task("user-a", task["taskId"])["attachmentKey"]
    assert stored == f"user-a/{task['taskId']}/my notes(1).pdf"


@pytest.mark.parametrize("key", ["", "junk", "a/b", "a/not-a-uuid/c.pdf", "a/b/c/d.pdf"])
def test_indexer_ignores_malformed_keys(backend, key):
    assert indexer(s3_event(key), None) == {"indexed": 0, "ignored": 1}


def test_indexer_never_creates_a_task(backend):
    task_id = new_id()
    assert indexer(s3_event(f"user-a/{task_id}/a.pdf"), None) == {"indexed": 0, "ignored": 1}
    assert get_store().get_task("user-a", task_id) is None


def test_indexer_handles_batch_and_empty(backend):
    good = create()
    event = {"Records": s3_event(f"user-a/{good['taskId']}/a.pdf")["Records"] + s3_event("junk")["Records"]}
    assert indexer(event, None) == {"indexed": 1, "ignored": 1}
    assert indexer({}, None) == {"indexed": 0, "ignored": 0}


# --- S3 specifics, with moto ---


@pytest.fixture
def s3_mode(aws):
    return boto3.client("s3", region_name="ap-south-1")


def test_presigned_post_policy(s3_mode):
    task = create()
    payload = body_of(
        handler(api_event("POST /tasks/{id}/attachment-url", body={"filename": "a.pdf"}, task_id=task["taskId"]), None)
    )
    # A regional URL, because the global endpoint would redirect and break browser CORS.
    assert "s3.ap-south-1.amazonaws.com" in payload["url"]
    assert "x-amz-signature" in payload["fields"]
    policy = json.loads(base64.b64decode(payload["fields"]["policy"]))
    assert ["content-length-range", 1, 10 * 1024 * 1024] in policy["conditions"]
    assert {"key": payload["key"]} in policy["conditions"]


def test_presigned_get_expiry_and_safe_display(s3_mode):
    task = create()
    key = f"user-a/{task['taskId']}/a.pdf"
    indexer(s3_event(key), None)
    response = handler(api_event("GET /tasks/{id}/attachment-url", task_id=task["taskId"]), None)
    assert response["statusCode"] == 200
    url = body_of(response)["url"]
    assert "X-Amz-Expires=300" in url and "s3.ap-south-1.amazonaws.com" in url
    assert "application%2Fpdf" in url and "inline" in url


def test_active_content_downloads_rather_than_renders():
    from shared.attachments import display_settings

    assert display_settings("u/t/page.html") == ("application/octet-stream", 'attachment; filename="page.html"')
    assert display_settings("u/t/pic.svg")[0] == "application/octet-stream"
    assert display_settings("u/t/notes.pdf") == ("application/pdf", 'inline; filename="notes.pdf"')


def test_delete_removes_s3_object(s3_mode):
    task = create()
    key = f"user-a/{task['taskId']}/a.pdf"
    s3_mode.put_object(Bucket=BUCKET, Key=key, Body=b"data")
    indexer(s3_event(key), None)
    assert handler(api_event("DELETE /tasks/{id}", task_id=task["taskId"]), None)["statusCode"] == 204
    assert s3_mode.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 0


def test_delete_succeeds_if_s3_cleanup_fails(s3_mode, monkeypatch):
    import functions.tasks_api.handler as module

    class BrokenAttachments:
        def delete(self, key):
            raise RuntimeError("S3 down")

    task = create()
    indexer(s3_event(f"user-a/{task['taskId']}/a.pdf"), None)
    monkeypatch.setattr(module, "get_attachments", BrokenAttachments)
    assert handler(api_event("DELETE /tasks/{id}", task_id=task["taskId"]), None)["statusCode"] == 204


def test_list_paginates_and_caps_at_limit(aws):
    store = get_store()
    tasks = [
        {"userId": "user-a", "taskId": new_id(), "title": "t" * 100, "dueDate": "2026-11-10", "status": "todo"}
        for _ in range(12)
    ]
    store.put_tasks(tasks)
    assert len(store.list_tasks("user-a", limit=5)[0]) == 5
    assert store.list_tasks("user-a", limit=5)[1] is True
    assert store.list_tasks("user-a", limit=12) == (store.list_tasks("user-a")[0], False)
