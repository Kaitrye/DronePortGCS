"""Temporary ORVD stub.

Approves AgroDron takeoff requests on the configured ORVD topic so demo
missions can start without a real external ORVD service.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from typing import Any, Dict

from broker.src.bus_factory import create_system_bus


def _topic() -> str:
    return os.environ.get("ORVD_TOPIC", "v1.ORVD.ORVD001.main").strip() or "v1.ORVD.ORVD001.main"


def _client_id() -> str:
    return os.environ.get("COMPONENT_ID", "orvd_stub").strip() or "orvd_stub"


def _build_response(message: Dict[str, Any]) -> Dict[str, Any]:
    payload = message.get("payload") if isinstance(message, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    return {
        "status": "takeoff_authorized",
        "approved": True,
        "mission_id": payload.get("mission_id"),
        "drone_id": payload.get("drone_id"),
        "issued_at": time.time(),
        "from": _client_id(),
    }


def main() -> None:
    topic = _topic()
    client_id = _client_id()
    retry_delay_s = float(os.environ.get("ORVD_STUB_RETRY_DELAY_S", "2.0"))
    running = True

    def handle_request(message: Dict[str, Any]) -> None:
        if not isinstance(message, dict):
            return
        action = str(message.get("action") or "").strip()
        reply_to = message.get("reply_to")
        correlation_id = message.get("correlation_id")
        if not reply_to or not correlation_id:
            return

        if action != "request_takeoff":
            bus.publish(
                reply_to,
                {
                    "correlation_id": correlation_id,
                    "approved": False,
                    "error": f"unsupported_action:{action}",
                    "from": client_id,
                },
            )
            return

        response = _build_response(message)
        response["correlation_id"] = correlation_id
        bus.publish(reply_to, response)
        print(f"[{client_id}] approved takeoff for mission={response.get('mission_id')} drone={response.get('drone_id')}")

    def handle_signal(sig: int, _frame: Any) -> None:
        nonlocal running
        print(f"[{client_id}] received signal {sig}, shutting down")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        bus = None
        subscribed = False
        try:
            bus = create_system_bus(client_id=client_id)
            bus.start()
            bus.subscribe(topic, handle_request)
            subscribed = True
            print(f"[{client_id}] ORVD stub started. Topic: {topic}")

            while running:
                time.sleep(1.0)
        except Exception as exc:
            if not running:
                break
            print(f"[{client_id}] broker connection failed: {exc}. Retrying in {retry_delay_s:.1f}s")
            time.sleep(retry_delay_s)
        finally:
            if bus is not None:
                if subscribed:
                    try:
                        bus.unsubscribe(topic)
                    except Exception:
                        pass
                try:
                    bus.stop()
                except Exception:
                    pass

    sys.exit(0)
