import json
import os
from typing import Iterable, Optional, Set, Tuple

from systems.drone_port.src.drone_manager.topics import DroneManagerActions
from systems.drone_port.src.orchestrator.topics import OrchestratorActions
from systems.drone_port.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions


PolicyKey = Tuple[str, str, str]


def component_topic() -> str:
    return (os.environ.get("COMPONENT_TOPIC") or ExternalTopics.DRONE_PORT).strip()


def audit_topic() -> str:
    return (os.environ.get("SECURITY_MONITOR_AUDIT_TOPIC") or "").strip()


def _get_float(name: str, default: float, *, min_value: Optional[float] = None) -> float:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        value = float(default)
    else:
        value = float(raw)
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    return value


def proxy_request_timeout_s() -> float:
    return _get_float("SECURITY_MONITOR_PROXY_REQUEST_TIMEOUT_S", 10.0, min_value=0.1)


def _normalize_policies(raw: Iterable[dict]) -> Set[PolicyKey]:
    parsed: Set[PolicyKey] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        sender = str(item.get("sender", "")).strip()
        topic = str(item.get("topic", "")).strip()
        action = str(item.get("action", "")).strip()
        if sender and topic and action:
            parsed.add((sender, topic, action))
    return parsed


def default_policies() -> Set[PolicyKey]:
    return {
        (ExternalTopics.OPERATOR, ExternalTopics.DRONE_PORT, OrchestratorActions.GET_AVAILABLE_DRONES),
        (ExternalTopics.AGRODRON, ExternalTopics.DRONE_PORT, DroneManagerActions.REQUEST_LANDING),
        (ExternalTopics.AGRODRON, ExternalTopics.DRONE_PORT, DroneManagerActions.REQUEST_TAKEOFF),
        (ExternalTopics.DRONE_PORT, ExternalTopics.SITL, SecurityMonitorActions.SITL_HOME_PUBLISH),
    }


def load_policies_from_env() -> Set[PolicyKey]:
    raw = (os.environ.get("SECURITY_MONITOR_POLICIES") or "").strip()
    if not raw:
        return default_policies()

    try:
        value = json.loads(raw)
        if isinstance(value, list):
            parsed = _normalize_policies(value)
            if parsed:
                return parsed
    except Exception:
        pass

    return default_policies()
