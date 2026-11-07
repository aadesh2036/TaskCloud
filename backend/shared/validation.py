"""Field validation shared by the tasks API and the planner agent."""

import re
from datetime import date, timedelta
from typing import Any

from shared.responses import bad_request

TITLE_MAX = 120
EST_MIN = 5
EST_MAX = 480
PRIORITIES = ("low", "medium", "high")
STATUSES = ("todo", "done")
PLAN_MAX_DAYS_AHEAD = 60
FILENAME_MAX = 100

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def is_valid_task_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_UUID4_RE.match(value))


def require_task_id(value: Any) -> str:
    if not is_valid_task_id(value):
        raise bad_request("Task ID is not a valid uuid4.")
    return value


def check_title(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("title must be a non-empty string")
    title = value.strip()
    if len(title) > TITLE_MAX:
        raise ValueError(f"title must be at most {TITLE_MAX} characters")
    return title


def check_date(value: Any) -> str:
    # The regex comes first, because date.fromisoformat also accepts forms like 20261107.
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError("dueDate must use the format YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("dueDate is not a real calendar date") from exc
    return value


def check_priority(value: Any) -> str:
    if value not in PRIORITIES:
        raise ValueError("priority must be low, medium or high")
    return value


def check_status(value: Any) -> str:
    if value not in STATUSES:
        raise ValueError("status must be todo or done")
    return value


def check_est_minutes(value: Any) -> int:
    # bool is a subclass of int in Python, so True would otherwise pass as 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("estMinutes must be a whole number")
    if not EST_MIN <= value <= EST_MAX:
        raise ValueError(f"estMinutes must be between {EST_MIN} and {EST_MAX}")
    return value


_NEW_TASK_FIELDS = {"title", "dueDate", "priority", "estMinutes"}
_PATCH_CHECKS = {
    "title": check_title,
    "dueDate": check_date,
    "priority": check_priority,
    "status": check_status,
    "estMinutes": check_est_minutes,
}


def _reject_unknown(body: dict, allowed: set[str]) -> None:
    unknown = sorted(set(body) - allowed)
    if unknown:
        raise bad_request(f"Unknown field(s): {', '.join(unknown)}.")


def clean_new_task(body: dict) -> dict:
    """Validate a POST /tasks body. userId, source and status are never accepted from it."""
    _reject_unknown(body, _NEW_TASK_FIELDS)
    if "title" not in body or "dueDate" not in body:
        raise bad_request("title and dueDate are required.")
    try:
        return {
            "title": check_title(body["title"]),
            "dueDate": check_date(body["dueDate"]),
            "priority": check_priority(body.get("priority", "medium")),
            "estMinutes": check_est_minutes(body.get("estMinutes", 30)),
        }
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


def clean_patch(body: dict) -> dict:
    """Validate a PATCH /tasks/{id} body."""
    _reject_unknown(body, set(_PATCH_CHECKS))
    if not body:
        raise bad_request("Provide at least one field to update.")
    try:
        return {field: _PATCH_CHECKS[field](value) for field, value in body.items()}
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


def clean_planned_task(raw: Any, today: date) -> dict:
    """Validate one task proposed by the model. Raises ValueError with a reason for the model.

    Only the four known fields are copied across, so anything else the model sends,
    such as a userId, is dropped here.
    """
    if not isinstance(raw, dict):
        raise ValueError("each task must be an object")
    task = {
        "title": check_title(raw.get("title")),
        "dueDate": check_date(raw.get("dueDate")),
        "priority": check_priority(raw.get("priority")),
        "estMinutes": check_est_minutes(raw.get("estMinutes")),
    }
    due = date.fromisoformat(task["dueDate"])
    if due < today:
        raise ValueError("dueDate is in the past")
    if due > today + timedelta(days=PLAN_MAX_DAYS_AHEAD):
        raise ValueError(f"dueDate is more than {PLAN_MAX_DAYS_AHEAD} days ahead")
    return task


def sanitize_filename(name: Any) -> str:
    """Make a filename safe to use as the last segment of an S3 key."""
    if not isinstance(name, str) or not name.strip():
        raise bad_request("filename is required.")
    # Browsers on Windows may send a full path. Only the last segment is the filename.
    base = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    safe = _UNSAFE_FILENAME_CHARS.sub("_", base).lstrip(".")
    if len(safe) > FILENAME_MAX:
        # Keep the end of the name, so the extension survives.
        safe = safe[-FILENAME_MAX:].lstrip(".")
    return safe or "file"


_KEY_USER_RE = re.compile(r"^[A-Za-z0-9-]+$")


def parse_attachment_key(key: str) -> tuple[str, str] | None:
    """Return (userId, taskId) from userId/taskId/filename, or None if malformed."""
    parts = key.split("/")
    if len(parts) != 3 or not all(parts):
        return None
    user_id, task_id, _filename = parts
    if not _KEY_USER_RE.match(user_id) or not is_valid_task_id(task_id):
        return None
    return user_id, task_id
