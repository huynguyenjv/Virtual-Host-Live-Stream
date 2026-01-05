import uuid
import time

def normalize_event(raw_event: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "type": raw_event.get("type", "COMMENT"),
        "content": raw_event.get("content", "").strip().lower(),
        "user": {
            "id": raw_event.get("user_id"),
            "name": raw_event.get("username")
        },
        "timestamp": int(time.time())
    }


def is_valid(event: dict) -> bool:
    if not event["content"]:
        return False
    if len(event["content"]) < 2:
        return False
    return True
