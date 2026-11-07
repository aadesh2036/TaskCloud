"""TaskCloud local dev server. Standard library only.

It plays the part of API Gateway and S3: it builds HTTP API 2.0 events, calls the real
Lambda handlers, and stores uploads in a folder. Run it with: python local/server.py
"""

import json
import os
import re
import sys
import time
import traceback
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "local"))

# Must be set before the backend picks a store. Local dev never touches DynamoDB by default.
os.environ.setdefault("TASKCLOUD_STORE", "local")

from functions.attachment_indexer.handler import lambda_handler as indexer_handler  # noqa: E402
from functions.planner_agent.handler import lambda_handler as planner_handler  # noqa: E402
from functions.tasks_api.handler import lambda_handler as tasks_handler  # noqa: E402
from shared.attachments import MAX_UPLOAD_BYTES, display_settings  # noqa: E402
from shared.store import default_data_dir  # noqa: E402
from shared.validation import parse_attachment_key  # noqa: E402
from stub_bedrock import StubBedrock  # noqa: E402

LOCAL_USER = "local-user"
DEFAULT_PORT = 8787
MAX_JSON_BYTES = 1024 * 1024
# Room for multipart boundaries and part headers around a 10 MB file.
MAX_UPLOAD_REQUEST_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
PLANNER_BUDGET_SECONDS = 28

_LOCALHOST_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

_ROUTES = [
    ("GET", re.compile(r"^/tasks$"), "GET /tasks"),
    ("POST", re.compile(r"^/tasks$"), "POST /tasks"),
    ("PATCH", re.compile(r"^/tasks/(?P<id>[^/]+)$"), "PATCH /tasks/{id}"),
    ("DELETE", re.compile(r"^/tasks/(?P<id>[^/]+)$"), "DELETE /tasks/{id}"),
    ("GET", re.compile(r"^/progress$"), "GET /progress"),
    ("POST", re.compile(r"^/tasks/(?P<id>[^/]+)/attachment-url$"), "POST /tasks/{id}/attachment-url"),
    ("GET", re.compile(r"^/tasks/(?P<id>[^/]+)/attachment-url$"), "GET /tasks/{id}/attachment-url"),
    ("POST", re.compile(r"^/plan$"), "POST /plan"),
]


def _match_route(method: str, path: str) -> tuple[str | None, dict]:
    for route_method, pattern, route_key in _ROUTES:
        match = pattern.match(path)
        if route_method == method and match:
            return route_key, match.groupdict()
    return None, {}


class LambdaContext:
    """Enough of the Lambda context for the planner's time check."""

    def __init__(self, budget_seconds: float):
        self._deadline = time.monotonic() + budget_seconds

    def get_remaining_time_in_millis(self) -> int:
        return int((self._deadline - time.monotonic()) * 1000)


def build_planner_kwargs() -> dict:
    """Choose the model client from PLANNER_MODE. Exits with a clear message if misconfigured."""
    mode = os.environ.get("PLANNER_MODE", "stub")
    if mode == "stub":
        return {"bedrock": StubBedrock(), "model_id": "local-stub"}
    if mode != "bedrock":
        sys.exit(f"PLANNER_MODE must be stub or bedrock, not {mode!r}.")
    model_id = os.environ.get("MODEL_ID")
    if not model_id:
        sys.exit("PLANNER_MODE=bedrock needs a MODEL_ID environment variable.")
    try:
        import boto3
    except ImportError:
        sys.exit("PLANNER_MODE=bedrock needs boto3. Run: pip install -r requirements-dev.txt")
    # Uses the developer's own AWS profile, and only ever calls Converse.
    return {"bedrock": boto3.client("bedrock-runtime"), "model_id": model_id}


def _uploads_root() -> Path:
    return default_data_dir() / "uploads"


def _safe_upload_path(key: str) -> Path | None:
    """Map a key to a path under the uploads folder, or None if it would escape it."""
    if parse_attachment_key(key) is None:
        return None
    root = _uploads_root().resolve()
    path = (root / key).resolve()
    return path if path.is_relative_to(root) else None


def parse_multipart(content_type: str, body: bytes) -> tuple[dict, bytes | None]:
    """Return (text fields, file bytes) from a multipart/form-data request body."""
    message = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)
    fields: dict[str, str] = {}
    file_bytes = None
    if not message.is_multipart():
        return fields, None
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        if name == "file":
            file_bytes = payload
        elif name:
            fields[name] = payload.decode("utf-8", "replace")
    return fields, file_bytes


class Handler(BaseHTTPRequestHandler):
    server_version = "TaskCloudLocal"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 - name comes from the base class
        sys.stderr.write(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}\n")

    # --- Helpers ---

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if _LOCALHOST_ORIGIN.match(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send(self, status: int, body: bytes = b"", headers: dict | None = None) -> None:
        self.send_response(status)
        self._cors_headers()
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode(), {"Content-Type": "application/json"})

    def _read_body(self, limit: int) -> bytes | None:
        """Read the request body, or return None if it is over the limit."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            # The unread body would corrupt the next request on a kept-alive connection.
            self.close_connection = True
            return None
        return self.rfile.read(length) if length else b""

    def _dispatch(self) -> None:
        try:
            path = urlsplit(self.path).path
            if self.command == "POST" and path == "/local/upload":
                self._handle_upload()
            elif self.command == "GET" and path.startswith("/local/files/"):
                self._handle_download(path)
            elif self.command == "GET" and path == "/":
                self._send_json(200, {"service": "taskcloud-local", "user": LOCAL_USER})
            else:
                self._handle_api(path)
        except Exception:
            traceback.print_exc()
            self._send_json(500, {"error": "InternalError", "message": "Local server error."})

    # --- API routes ---

    def _handle_api(self, path: str) -> None:
        route_key, path_params = _match_route(self.command, path)
        if route_key is None:
            self._send_json(404, {"message": "Not Found"})
            return

        # API Gateway rejects a missing token before Lambda runs, with this exact body.
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            self._read_body(MAX_JSON_BYTES)
            self._send_json(401, {"message": "Unauthorized"})
            return

        body = self._read_body(MAX_JSON_BYTES)
        if body is None:
            self._send_json(413, {"error": "PayloadTooLarge", "message": "Request body is too large."})
            return

        event = {
            "version": "2.0",
            "routeKey": route_key,
            "rawPath": path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "requestContext": {
                "http": {"method": self.command, "path": path},
                "authorizer": {"jwt": {"claims": {"sub": LOCAL_USER}}},
            },
            "pathParameters": path_params or None,
            "body": body.decode("utf-8", "replace") if body else None,
            "isBase64Encoded": False,
        }
        if route_key == "POST /plan":
            context = LambdaContext(PLANNER_BUDGET_SECONDS)
            response = planner_handler(event, context, **self.server.planner_kwargs)
        else:
            response = tasks_handler(event, None)
        self._send(
            response["statusCode"],
            (response.get("body") or "").encode(),
            {"Content-Type": response.get("headers", {}).get("content-type", "application/json")},
        )

    # --- Stand-ins for S3 ---

    def _handle_upload(self) -> None:
        body = self._read_body(MAX_UPLOAD_REQUEST_BYTES)
        if body is None:
            self._send_json(413, {"error": "PayloadTooLarge", "message": "Files can be at most 10 MB."})
            return
        fields, file_bytes = parse_multipart(self.headers.get("Content-Type", ""), body)
        key = fields.get("key", "")
        path = _safe_upload_path(key)
        if path is None or file_bytes is None or not key.startswith(f"{LOCAL_USER}/"):
            self._send_json(400, {"error": "BadRequest", "message": "Upload needs a valid key and a file."})
            return
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            self._send_json(413, {"error": "PayloadTooLarge", "message": "Files can be at most 10 MB."})
            return
        if not file_bytes:
            self._send_json(400, {"error": "BadRequest", "message": "The file is empty."})
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        # Keys in real S3 events are URL-encoded, so the synthetic event encodes them too.
        event = {"Records": [{"s3": {"bucket": {"name": "local"}, "object": {"key": quote_plus(key, safe="/")}}}]}
        indexer_handler(event, None)
        self._send(204)  # the same status S3 gives a successful POST

    def _handle_download(self, path: str) -> None:
        key = unquote(path[len("/local/files/"):])
        file_path = _safe_upload_path(key)
        if file_path is None or not file_path.is_file():
            self._send_json(404, {"error": "NotFound", "message": "No such file."})
            return
        content_type, disposition = display_settings(key)
        self._send(200, file_path.read_bytes(), {"Content-Type": content_type, "Content-Disposition": disposition})

    # --- Methods ---

    def do_OPTIONS(self):  # noqa: N802 - name comes from the base class
        self.send_response(204)
        self._cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_POST = do_PATCH = do_DELETE = _dispatch  # noqa: N815


def create_server(port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    # 127.0.0.1 only: this server accepts any token, so it must not be reachable from the network.
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.planner_kwargs = build_planner_kwargs()
    return server


def main() -> None:
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    os.environ.setdefault("TASKCLOUD_LOCAL_BASE_URL", f"http://localhost:{port}")
    server = create_server(port)
    print(f"TaskCloud local API on http://localhost:{port}", flush=True)
    print(f"  store:   {os.environ['TASKCLOUD_STORE']} ({default_data_dir()})", flush=True)
    print(f"  planner: {os.environ.get('PLANNER_MODE', 'stub')}", flush=True)
    print("  Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
