from __future__ import annotations

from typing import Any, Dict, Optional

from systems.agrodron.sdk.topic_utils import topic_for


def publish_journal_event(
    bus: Any,
    sender: str,
    event: str,
    *,
    source: str,
    details: Optional[Dict[str, Any]] = None,
) -> bool:
    return bus.publish(
        topic_for("security_monitor"),
        {
            "action": "proxy_publish",
            "sender": sender,
            "payload": {
                "target": {
                    "topic": topic_for("journal"),
                    "action": "log_event",
                },
                "data": {
                    "event": event,
                    "source": source,
                    "details": details or {},
                },
            },
        },
    )
