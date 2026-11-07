"""taskcloud-tasks-api: all task routes and progress."""

import logging
import uuid

from shared.attachments import MAX_UPLOAD_BYTES, URL_EXPIRY_SECONDS, get_attachments
from shared.progress import compute_progress
from shared.responses import (
    ApiError,
    bad_request,
    error_response,
    get_user_id,
    internal_error,
    json_response,
    not_found,
    parse_json_object,
)
from shared.store import TaskNotFound, get_store
from shared.timeutil import iso_utc, now_utc
from shared.validation import clean_new_task, clean_patch, require_task_id, sanitize_filename

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _task_id(event: dict) -> str:
    return require_task_id((event.get("pathParameters") or {}).get("id"))


def list_tasks(event: dict, user_id: str) -> dict:
    tasks, truncated = get_store().list_tasks(user_id, consistent=True)
    return json_response(200, {"tasks": tasks, "truncated": truncated})


def create_task(event: dict, user_id: str) -> dict:
    fields = clean_new_task(parse_json_object(event))
    task = {
        **fields,
        "userId": user_id,
        "taskId": str(uuid.uuid4()),
        "status": "todo",
        "source": "manual",
        "createdAt": iso_utc(now_utc()),
    }
    get_store().put_task(task)
    return json_response(201, task)


def update_task(event: dict, user_id: str) -> dict:
    task_id = _task_id(event)
    fields = clean_patch(parse_json_object(event))
    removes: tuple[str, ...] = ()
    set_if_absent = {}
    if fields.get("status") == "done":
        # if_not_exists: completing a task twice must not move it to a later day's count.
        set_if_absent["completedAt"] = iso_utc(now_utc())
    elif fields.get("status") == "todo":
        removes = ("completedAt",)
    try:
        task = get_store().update_task(user_id, task_id, fields, removes=removes, set_if_absent=set_if_absent)
    except TaskNotFound as exc:
        raise not_found() from exc
    return json_response(200, task)


def delete_task(event: dict, user_id: str) -> dict:
    task_id = _task_id(event)
    try:
        task = get_store().delete_task(user_id, task_id)
    except TaskNotFound as exc:
        raise not_found() from exc
    key = task.get("attachmentKey")
    if key:
        try:
            get_attachments().delete(key)
        except Exception:
            # The task is already gone, so report success. A stray file costs far less
            # than telling the student the delete failed when it did not.
            logger.exception("Could not delete attachment for task %s", task_id)
    return json_response(204)


def get_progress(event: dict, user_id: str) -> dict:
    # Eventually consistent on purpose: cheaper, and a short delay does not matter here.
    tasks, _ = get_store().list_tasks(user_id, consistent=False)
    return json_response(200, compute_progress(tasks, now_utc()))


def create_upload_url(event: dict, user_id: str) -> dict:
    task_id = _task_id(event)
    body = parse_json_object(event)
    filename = sanitize_filename(body.get("filename"))

    size = body.get("size")
    if size is not None:
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise bad_request("size must be a positive whole number of bytes.")
        if size > MAX_UPLOAD_BYTES:
            raise ApiError(413, "PayloadTooLarge", "Files can be at most 10 MB.")

    # Tasks are read from the caller's own partition, so this is the ownership check.
    task = get_store().get_task(user_id, task_id)
    if task is None:
        raise not_found()
    if task.get("attachmentKey"):
        raise ApiError(409, "Conflict", "This task already has a file attached.")

    key = f"{user_id}/{task_id}/{filename}"
    upload = get_attachments().presign_upload(key)
    return json_response(200, {**upload, "key": key, "expiresIn": URL_EXPIRY_SECONDS, "maxBytes": MAX_UPLOAD_BYTES})


def create_download_url(event: dict, user_id: str) -> dict:
    task_id = _task_id(event)
    task = get_store().get_task(user_id, task_id)
    if task is None:
        raise not_found()
    key = task.get("attachmentKey")
    if not key:
        raise not_found("This task has no file attached.")
    return json_response(200, {"url": get_attachments().presign_download(key), "expiresIn": URL_EXPIRY_SECONDS})


ROUTES = {
    "GET /tasks": list_tasks,
    "POST /tasks": create_task,
    "PATCH /tasks/{id}": update_task,
    "DELETE /tasks/{id}": delete_task,
    "GET /progress": get_progress,
    "POST /tasks/{id}/attachment-url": create_upload_url,
    "GET /tasks/{id}/attachment-url": create_download_url,
}


def lambda_handler(event: dict, context: object) -> dict:
    try:
        user_id = get_user_id(event)
        route = ROUTES.get(event.get("routeKey"))
        if route is None:
            raise ApiError(404, "NotFound", "No such route.")
        return route(event, user_id)
    except ApiError as error:
        return error_response(error)
    except Exception:
        logger.exception("Unhandled error on %s", event.get("routeKey"))
        return internal_error()
