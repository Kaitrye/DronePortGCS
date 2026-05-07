import json
import os
from typing import Iterable, Optional, Set, Tuple

from systems.gcs.src.orchestrator.topics import OrchestratorActions
from systems.gcs.src.security_monitor.topics import ExternalTopics
from systems.gcs.topics import DroneActions


PolicyKey = Tuple[str, str, str]


def component_topic() -> str:
    return (os.environ.get("COMPONENT_TOPIC") or ExternalTopics.GCS).strip()


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


def journal_file_path() -> str:
    return (
        os.environ.get("SECURITY_JOURNAL_FILE_PATH")
        or "/var/log/drones/security_journal.ndjson"
    ).strip()


def journal_min_severity() -> str:
    return (os.environ.get("SECURITY_JOURNAL_MIN_SEVERITY") or "info").strip().lower()


def service_name() -> str:
    return "GCS"


def service_id() -> int:
    raw = os.environ.get("SECURITY_JOURNAL_SERVICE_ID")
    if raw is None or str(raw).strip() == "":
        return 1
    try:
        value = int(raw)
    except ValueError:
        return 1
    if value < 1 or value > 1000:
        return 1
    return value


def infopanel_url() -> str:
    return (os.environ.get("INFOPANEL_URL") or "").strip()


def infopanel_api_key() -> str:
    return (os.environ.get("INFOPANEL_API_KEY") or "").strip()


def infopanel_batch_size() -> int:
    raw = (os.environ.get("INFOPANEL_BATCH_SIZE") or "").strip()
    if not raw:
        return 50
    try:
        value = int(raw)
    except ValueError:
        return 50
    return max(1, min(value, 100))


def infopanel_flush_interval_s() -> float:
    return _get_float("INFOPANEL_FLUSH_INTERVAL_S", 5.0, min_value=0.1)


def infopanel_max_retries() -> int:
    raw = (os.environ.get("INFOPANEL_MAX_RETRIES") or "").strip()
    if not raw:
        return 5
    try:
        return max(0, int(raw))
    except ValueError:
        return 5


def infopanel_verify_tls() -> bool:
    return (os.environ.get("INFOPANEL_VERIFY_TLS") or "true").strip().lower() != "false"


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
        (ExternalTopics.OPERATOR, ExternalTopics.GCS, OrchestratorActions.TASK_SUBMIT),
        (ExternalTopics.OPERATOR, ExternalTopics.GCS, OrchestratorActions.TASK_ASSIGN),
        (ExternalTopics.OPERATOR, ExternalTopics.GCS, OrchestratorActions.TASK_START),
        (ExternalTopics.GCS, ExternalTopics.AGRODRON, DroneActions.LOAD_MISSION),
        (ExternalTopics.GCS, ExternalTopics.AGRODRON, DroneActions.CMD),
        (ExternalTopics.GCS, ExternalTopics.AGRODRON, DroneActions.TELEMETRY_GET),
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
