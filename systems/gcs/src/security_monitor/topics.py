"""Topics and actions for GCS security monitor."""

from sdk.topic_naming import clean_topic_part


def build_topic_comp(name: str) -> str:
    return f"systems.{clean_topic_part(name)}"


class ExternalTopics:
    OPERATOR = build_topic_comp("operator")
    GCS = build_topic_comp("gcs")
    AGRODRON = build_topic_comp("agrodron")
    SITL = build_topic_comp("sitl")


class SecurityMonitorActions:
    PROXY_REQUEST = "proxy_request"
    PROXY_PUBLISH = "proxy_publish"
    LIST_POLICIES = "list_policies"
    LOG_EVENT = "log_event"


__all__ = [
    "build_topic_comp",
    "ExternalTopics",
    "SecurityMonitorActions",
]
