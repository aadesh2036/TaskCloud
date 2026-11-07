"""HTTP API (payload format 2.0) responses, errors and request helpers."""

import base64
import json
from decimal import Decimal
from typing import Any


class ApiError(Exception):
    """An error that maps directly to an HTTP response."""

    def __init__(self, status: int, error: str, message: str):
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


def bad_request(message: str) -> ApiError:
    return ApiError(400, "BadRequest", message)


def not_found(message: str = "Task not found.") -> ApiError:
    return ApiError(404, "NotFound", message)


def _json_default(value: Any) -> Any:
    # DynamoDB returns numbers as Decimal, which json cannot serialize.
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def json_response(status: int, payload: Any = None) -> dict:
    # No CORS headers here: API Gateway adds them, and overrides any that Lambda sets.
    response = {"statusCode": status, "headers": {"content-type": "application/json"}}
    if payload is not None:
        response["body"] = json.dumps(payload, default=_json_default)
    return response


def error_response(error: ApiError) -> dict:
    return json_response(error.status, {"error": error.error, "message": error.message})


def internal_error() -> dict:
    # A fixed message, so exception details never reach the browser. They go to the logs.
    return json_response(500, {"error": "InternalError", "message": "Something went wrong. Please try again."})


def get_user_id(event: dict) -> str:
    """Return the Cognito sub from the verified JWT.

    This is the only source of a user ID anywhere in the backend. API Gateway has already
    checked the token signature, so these claims can be trusted, unlike the request body.
    """
    try:
        user_id = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    except (KeyError, TypeError):
        user_id = None
    if not user_id or not isinstance(user_id, str):
        raise ApiError(401, "Unauthorized", "Missing or invalid token.")
    return user_id


def parse_json_object(event: dict) -> dict:
    """Parse the request body, which must be a JSON object."""
    raw = event.get("body")
    if raw is None or raw == "":
        return {}
    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise bad_request("Request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise bad_request("Request body must be a JSON object.")
    return body
