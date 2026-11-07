"""End-to-end smoke test of every route and the stub planner against a running local server.

Usage: python local/smoke_test.py [base_url]    (default http://localhost:8787)
Standard library only. It removes the tasks it creates. Exits 0 if everything passed.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BOUNDARY = "----taskcloudsmoketest"
TOKEN = {"Authorization": "Bearer local-smoke-test"}
TEN_MB = 10 * 1024 * 1024
# Bytes a careless multipart parser would corrupt, including bare CR, LF and CRLF.
BINARY = bytes(range(256)) + b"\r\n--not-a-boundary\r\n\n\r\x00end"


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(self, method, path, body=None, headers=None, raw=None, url=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        merged = dict(headers if headers is not None else TOKEN)
        if body is not None:
            merged["Content-Type"] = "application/json"
        request = urllib.request.Request(url or self.base_url + path, data=data, headers=merged, method=method)
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(), dict(error.headers)

    def json(self, method, path, body=None, headers=None):
        status, payload, _ = self.request(method, path, body, headers)
        return status, json.loads(payload) if payload else None


def multipart(fields: dict, file_bytes: bytes) -> tuple[bytes, dict]:
    parts = []
    for name, value in fields.items():
        parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="f"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    parts.append(file_bytes)
    parts.append(f"\r\n--{BOUNDARY}--\r\n".encode())
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"}


def run(base_url: str) -> list[str]:
    """Run all checks and return a list of failures."""
    client = Client(base_url)
    failures: list[str] = []
    created: list[str] = []

    def check(name, condition, detail=""):
        print(f"  {'ok  ' if condition else 'FAIL'} {name}")
        if not condition:
            failures.append(f"{name} {detail}".strip())

    due = (date.today() + timedelta(days=3)).isoformat()
    missing_id = "00000000-0000-4000-8000-000000000000"

    print("Auth and CORS")
    status, _ = client.json("GET", "/tasks", headers={})
    check("no token gets 401", status == 401, status)
    status, _ = client.json("POST", "/plan", {"prompt": "x"}, headers={})
    check("no token on /plan gets 401", status == 401, status)
    status, _, headers = client.request(
        "OPTIONS",
        "/tasks",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    allowed = headers.get("Access-Control-Allow-Origin")
    check("preflight allows localhost", status == 204 and allowed == "http://localhost:5173", allowed)
    _, _, headers = client.request("OPTIONS", "/tasks", headers={"Origin": "http://evil.example"})
    check("preflight refuses other origins", "Access-Control-Allow-Origin" not in headers)
    check("unknown route gets 404", client.json("GET", "/nope")[0] == 404)

    print("Tasks")
    status, payload = client.json("POST", "/tasks", {"title": "", "dueDate": due})
    check("invalid task gets 400 with error shape", status == 400 and {"error", "message"} <= set(payload), payload)
    status, payload = client.json("POST", "/tasks", {"title": "x", "dueDate": due, "userId": "victim"})
    check("userId in body gets 400", status == 400, status)

    status, task = client.json(
        "POST", "/tasks", {"title": "Smoke test task", "dueDate": due, "priority": "high", "estMinutes": 25}
    )
    check("POST /tasks creates a task", status == 201 and task["source"] == "manual" and task["status"] == "todo", task)
    task_id = task["taskId"]
    created.append(task_id)

    status, payload = client.json("GET", "/tasks")
    check("GET /tasks includes it", status == 200 and task_id in [t["taskId"] for t in payload["tasks"]])

    status, payload = client.json("PATCH", f"/tasks/{task_id}", {"title": "Renamed"})
    check("PATCH renames", status == 200 and payload["title"] == "Renamed", payload)
    check("PATCH bad field gets 400", client.json("PATCH", f"/tasks/{task_id}", {"source": "agent"})[0] == 400)
    check("PATCH bad ID gets 400", client.json("PATCH", "/tasks/not-a-uuid", {"title": "x"})[0] == 400)
    check("PATCH missing task gets 404", client.json("PATCH", f"/tasks/{missing_id}", {"title": "x"})[0] == 404)

    print("Progress")
    _, before = client.json("GET", "/progress")
    status, done = client.json("PATCH", f"/tasks/{task_id}", {"status": "done"})
    check("completing sets completedAt", status == 200 and done.get("completedAt"), done)
    status, after = client.json("GET", "/progress")
    check(
        "GET /progress counts it",
        status == 200
        and after["done"] == before["done"] + 1
        and after["completedToday"] == before["completedToday"] + 1
        and after["streakDays"] >= 1
        and len(after["last7Days"]) == 7
        and set(after["last7Days"][0]) == {"date", "done"},
        after,
    )
    status, reopened = client.json("PATCH", f"/tasks/{task_id}", {"status": "todo"})
    check("reopening removes completedAt", status == 200 and "completedAt" not in reopened, reopened)

    print("Attachments")
    path = f"/tasks/{task_id}/attachment-url"
    check("GET URL with no file gets 404", client.json("GET", path)[0] == 404)
    check("too large gets 413", client.json("POST", path, {"filename": "a.pdf", "size": TEN_MB + 1})[0] == 413)
    check("missing filename gets 400", client.json("POST", path, {})[0] == 400)
    status, _ = client.json("POST", f"/tasks/{missing_id}/attachment-url", {"filename": "a"})
    check("upload URL for missing task gets 404", status == 404, status)

    status, upload = client.json("POST", path, {"filename": "my notes.pdf", "size": len(BINARY)})
    check("POST attachment-url returns url and fields", status == 200 and upload["url"] and upload["fields"], upload)
    check("key is sanitized", upload["key"].endswith(f"/{task_id}/my_notes.pdf"), upload["key"])

    raw, headers = multipart(upload["fields"], b"x" * (TEN_MB + 1))
    status, _, _ = client.request("POST", "", raw=raw, headers=headers, url=upload["url"])
    check("real oversized upload gets 413", status == 413, status)

    raw, headers = multipart({"key": "other-user/" + upload["key"].split("/", 1)[1]}, BINARY)
    status, _, _ = client.request("POST", "", raw=raw, headers=headers, url=upload["url"])
    check("upload to another user's key is refused", status == 400, status)

    raw, headers = multipart(upload["fields"], BINARY)
    status, _, _ = client.request("POST", "", raw=raw, headers=headers, url=upload["url"])
    check("upload succeeds", status == 204, status)

    _, listed = client.json("GET", "/tasks")
    stored = next(t for t in listed["tasks"] if t["taskId"] == task_id)
    check("indexer linked the file", stored.get("attachmentKey") == upload["key"], stored)
    check("second attachment gets 409", client.json("POST", path, {"filename": "b.pdf"})[0] == 409)

    status, download = client.json("GET", path)
    check("GET attachment-url returns a URL", status == 200 and download["url"], download)
    status, content, headers = client.request("GET", "", headers={}, url=download["url"])
    check("file round-trips byte for byte", status == 200 and content == BINARY, f"{status} {len(content)}")
    check("PDF opens inline", headers.get("Content-Disposition", "").startswith("inline"), headers)

    status, _, _ = client.request("GET", "", headers={}, url=client.base_url + "/local/files/..%2F..%2Ftasks.json")
    check("path traversal is refused", status == 404, status)

    print("Planner (stub)")
    check("empty prompt gets 400", client.json("POST", "/plan", {"prompt": ""})[0] == 400)
    check("long prompt gets 400", client.json("POST", "/plan", {"prompt": "x" * 1001})[0] == 400)
    status, plan = client.json("POST", "/plan", {"prompt": "DBMS exam on Friday, finish my lab record"})
    check("POST /plan returns a summary", status == 200 and plan["summary"], plan)
    all_agent = plan["tasks"] and all(t["source"] == "agent" for t in plan["tasks"])
    check("tasks are saved with source agent", all_agent, plan)
    check("nothing rejected", plan["rejected"] == [], plan)
    created += [t["taskId"] for t in plan["tasks"]]
    _, listed = client.json("GET", "/tasks")
    ids = {t["taskId"] for t in listed["tasks"]}
    check("plan tasks appear in GET /tasks", all(t["taskId"] in ids for t in plan["tasks"]))

    print("Delete and clean up")
    status, _ = client.json("DELETE", f"/tasks/{task_id}")
    check("DELETE gets 204", status == 204, status)
    status, _, _ = client.request("GET", "", headers={}, url=download["url"])
    check("attachment file is deleted too", status == 404, status)
    check("deleting again gets 404", client.json("DELETE", f"/tasks/{task_id}")[0] == 404)
    for leftover in created:
        client.request("DELETE", f"/tasks/{leftover}")

    return failures


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8787"
    print(f"Smoke testing {base_url}")
    try:
        failures = run(base_url)
    except urllib.error.URLError as error:
        print(f"Could not reach the server: {error}. Start it with: python local/server.py")
        return 1
    if failures:
        print(f"\n{len(failures)} check(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
