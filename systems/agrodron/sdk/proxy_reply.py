from __future__ import annotations

from typing import Any, Dict, Optional


def unwrap_proxy_target_response(response: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    cur: Any = response
    for _ in range(6):
        if not isinstance(cur, dict):
            return None
        target_response = cur.get("target_response")
        if isinstance(target_response, dict):
            cur = target_response
            continue
        payload = cur.get("payload")
        if isinstance(payload, dict):
            nested = payload.get("target_response")
            if isinstance(nested, dict):
                cur = nested
                continue
        return cur
    return cur if isinstance(cur, dict) else None


def extract_navigation_nav_state_from_target_response(
    target_response: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    unwrapped = unwrap_proxy_target_response(target_response)
    if not isinstance(unwrapped, dict):
        return None
    payload = unwrapped.get("payload")
    if isinstance(payload, dict):
        if "nav_state" in payload and isinstance(payload["nav_state"], dict):
            return payload["nav_state"]
        return payload
    return unwrapped
