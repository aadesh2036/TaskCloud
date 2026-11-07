"""taskcloud-attachment-indexer: links an uploaded file to its task.

Triggered by S3 ObjectCreated events, so nobody is waiting on the response.
"""

import logging
from urllib.parse import unquote_plus

from shared.store import get_store
from shared.validation import parse_attachment_key

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context: object) -> dict:
    indexed = ignored = 0
    for record in event.get("Records", []):
        # S3 URL-encodes keys in events. Spaces arrive as "+", hence unquote_plus.
        key = unquote_plus(record.get("s3", {}).get("object", {}).get("key", ""))
        parsed = parse_attachment_key(key)
        if parsed is None:
            logger.warning("Ignoring malformed key: %r", key)
            ignored += 1
            continue
        user_id, task_id = parsed
        # A real DynamoDB failure is deliberately not caught: Lambda then retries the event.
        if get_store().set_attachment(user_id, task_id, key):
            indexed += 1
        else:
            # The task was deleted between the upload URL and the upload finishing.
            # This role cannot delete objects, so the file stays until teardown.
            logger.warning("Task %s no longer exists for key: %r", task_id, key)
            ignored += 1
    return {"indexed": indexed, "ignored": ignored}
