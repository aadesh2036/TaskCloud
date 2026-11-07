"""Task storage. TASKCLOUD_STORE selects DynamoDB (Lambda) or a JSON file (local dev).

Both backends have the same methods and raise the same errors, so handlers and tests
do not care which one is active.
"""

import json
import os
import threading
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

LIST_LIMIT = 500


class TaskNotFound(Exception):
    pass


def default_data_dir() -> Path:
    configured = os.environ.get("TASKCLOUD_DATA_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "local" / ".data"


def _plain(item: dict) -> dict:
    # DynamoDB returns every number as Decimal. Tool results sent to Bedrock must be
    # plain JSON types, so items are normalized as soon as they leave the store.
    return {k: int(v) if isinstance(v, Decimal) else v for k, v in item.items()}


class DynamoStore:
    def __init__(self, table_name: str):
        # Imported here so that local mode runs with no third-party packages installed.
        import boto3

        self._table = boto3.resource("dynamodb").Table(table_name)

    def list_tasks(self, user_id: str, consistent: bool = True, limit: int = LIST_LIMIT) -> tuple[list[dict], bool]:
        """Return (tasks, truncated). DynamoDB pages at 1 MB, so this may take several queries."""
        from boto3.dynamodb.conditions import Key

        items: list[dict] = []
        kwargs = {"KeyConditionExpression": Key("userId").eq(user_id), "ConsistentRead": consistent}
        while True:
            page = self._table.query(Limit=limit - len(items), **kwargs)
            items.extend(_plain(i) for i in page.get("Items", []))
            last_key = page.get("LastEvaluatedKey")
            if not last_key:
                return items, False
            if len(items) >= limit:
                return items, True
            kwargs["ExclusiveStartKey"] = last_key

    def get_task(self, user_id: str, task_id: str) -> dict | None:
        result = self._table.get_item(Key={"userId": user_id, "taskId": task_id}, ConsistentRead=True)
        item = result.get("Item")
        return _plain(item) if item else None

    def put_task(self, task: dict) -> None:
        self._table.put_item(Item=task)

    def put_tasks(self, tasks: list[dict]) -> None:
        # batch_writer resends any UnprocessedItems, which BatchWriteItem can return.
        with self._table.batch_writer() as batch:
            for task in tasks:
                batch.put_item(Item=task)

    def update_task(
        self,
        user_id: str,
        task_id: str,
        sets: dict,
        removes: tuple[str, ...] = (),
        set_if_absent: dict | None = None,
    ) -> dict:
        """Update an existing task. set_if_absent keeps a value that is already there."""
        set_if_absent = set_if_absent or {}
        names, values, set_parts = {}, {}, []
        for i, (field, value) in enumerate(sets.items()):
            names[f"#s{i}"], values[f":s{i}"] = field, value
            set_parts.append(f"#s{i} = :s{i}")
        for i, (field, value) in enumerate(set_if_absent.items()):
            names[f"#a{i}"], values[f":a{i}"] = field, value
            set_parts.append(f"#a{i} = if_not_exists(#a{i}, :a{i})")
        remove_parts = []
        for i, field in enumerate(removes):
            names[f"#r{i}"] = field
            remove_parts.append(f"#r{i}")
        expression = ""
        if set_parts:
            expression += "SET " + ", ".join(set_parts)
        if remove_parts:
            expression += " REMOVE " + ", ".join(remove_parts)

        kwargs = {"ExpressionAttributeValues": values} if values else {}
        client_error = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            result = self._table.update_item(
                Key={"userId": user_id, "taskId": task_id},
                UpdateExpression=expression.strip(),
                ConditionExpression="attribute_exists(taskId)",
                ExpressionAttributeNames=names,
                ReturnValues="ALL_NEW",
                **kwargs,
            )
        except client_error as exc:
            raise TaskNotFound(task_id) from exc
        return _plain(result["Attributes"])

    def set_attachment(self, user_id: str, task_id: str, key: str) -> bool:
        """Set attachmentKey. Returns False if the task no longer exists.

        Separate from update_task because the indexer role has only UpdateItem, and
        asking for ALL_NEW would be pointless here.
        """
        client_error = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            self._table.update_item(
                Key={"userId": user_id, "taskId": task_id},
                UpdateExpression="SET attachmentKey = :key",
                ConditionExpression="attribute_exists(taskId)",
                ExpressionAttributeValues={":key": key},
            )
        except client_error:
            return False
        return True

    def delete_task(self, user_id: str, task_id: str) -> dict:
        """Delete a task and return what it held, so the caller can clean up its file."""
        client_error = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            result = self._table.delete_item(
                Key={"userId": user_id, "taskId": task_id},
                ConditionExpression="attribute_exists(taskId)",
                ReturnValues="ALL_OLD",
            )
        except client_error as exc:
            raise TaskNotFound(task_id) from exc
        return _plain(result["Attributes"])


class LocalStore:
    """A JSON file shaped as {userId: {taskId: task}}. For local development only."""

    def __init__(self, path: Path):
        self._path = path
        # The local server is threaded, and a read-modify-write of the file must not interleave.
        self._lock = threading.RLock()

    def _load(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(temp, self._path)

    def list_tasks(self, user_id: str, consistent: bool = True, limit: int = LIST_LIMIT) -> tuple[list[dict], bool]:
        with self._lock:
            tasks = sorted(self._load().get(user_id, {}).values(), key=lambda t: t["taskId"])
        return tasks[:limit], len(tasks) > limit

    def get_task(self, user_id: str, task_id: str) -> dict | None:
        with self._lock:
            return self._load().get(user_id, {}).get(task_id)

    def put_task(self, task: dict) -> None:
        self.put_tasks([task])

    def put_tasks(self, tasks: list[dict]) -> None:
        with self._lock:
            data = self._load()
            for task in tasks:
                data.setdefault(task["userId"], {})[task["taskId"]] = task
            self._save(data)

    def update_task(
        self,
        user_id: str,
        task_id: str,
        sets: dict,
        removes: tuple[str, ...] = (),
        set_if_absent: dict | None = None,
    ) -> dict:
        with self._lock:
            data = self._load()
            task = data.get(user_id, {}).get(task_id)
            if task is None:
                raise TaskNotFound(task_id)
            task.update(sets)
            for field, value in (set_if_absent or {}).items():
                task.setdefault(field, value)
            for field in removes:
                task.pop(field, None)
            self._save(data)
            return task

    def set_attachment(self, user_id: str, task_id: str, key: str) -> bool:
        try:
            self.update_task(user_id, task_id, {"attachmentKey": key})
        except TaskNotFound:
            return False
        return True

    def delete_task(self, user_id: str, task_id: str) -> dict:
        with self._lock:
            data = self._load()
            task = data.get(user_id, {}).pop(task_id, None)
            if task is None:
                raise TaskNotFound(task_id)
            self._save(data)
            return task


@lru_cache(maxsize=1)
def get_store() -> DynamoStore | LocalStore:
    """Return the store for this container. Cached, so warm Lambdas reuse the connection."""
    if os.environ.get("TASKCLOUD_STORE", "dynamodb") == "local":
        return LocalStore(default_data_dir() / "tasks.json")
    return DynamoStore(os.environ["TABLE_NAME"])
