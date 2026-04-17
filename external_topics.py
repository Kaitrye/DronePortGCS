"""Внешние топики для интеграции GCS с AgroDron и смежными системами."""

from __future__ import annotations

import os
import re

from sdk.topic_naming import build_component_topic


def _clean(val: str) -> str:
    return re.sub(r"[\s/\\]+", "_", val.strip()).strip("_") if val else val


def _env(name: str, default: str) -> str:
    return _clean(os.getenv(name, default)) or default


def _agrodron_topic(suffix: str, env_override: str) -> str:
    override = os.getenv(env_override, "").strip()
    if override:
        return override
    return build_component_topic(
        suffix,
        system_env_var="AGRODRON_SYSTEM_NAME",
        default_system_name="Agrodron",
    )


class ExternalTopics:
    AGRODRON_SECURITY_MONITOR = _agrodron_topic(
        "security_monitor",
        "AGRODRON_SECURITY_MONITOR_TOPIC",
    )
    AGRODRON_MISSION_HANDLER = _agrodron_topic(
        "mission_handler",
        "AGRODRON_MISSION_HANDLER_TOPIC",
    )
    AGRODRON_AUTOPILOT = _agrodron_topic(
        "autopilot",
        "AGRODRON_AUTOPILOT_TOPIC",
    )
    AGRODRON_TELEMETRY = _agrodron_topic(
        "telemetry",
        "AGRODRON_TELEMETRY_TOPIC",
    )

    @classmethod
    def agrodron_all(cls) -> list[str]:
        return [
            cls.AGRODRON_SECURITY_MONITOR,
            cls.AGRODRON_MISSION_HANDLER,
            cls.AGRODRON_AUTOPILOT,
            cls.AGRODRON_TELEMETRY,
        ]


__all__ = ["ExternalTopics"]
