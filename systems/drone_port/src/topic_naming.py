"""Utilities for versioned, instance-safe topic naming."""

from __future__ import annotations

import os


def _clean(value: str) -> str:
    return (value or "").strip().replace("/", ".")


def topic_version() -> str:
    return _clean(os.getenv("TOPIC_VERSION", "v1")) or "v1"


def system_name() -> str:
    return _clean(os.getenv("SYSTEM_NAME", "droneport")) or "droneport"


def instance_id() -> str:
    return _clean(os.getenv("INSTANCE_ID", "1")) or "1"


def build_component_topic(component: str) -> str:
    component_name = _clean(component)
    return f"{topic_version()}.{system_name()}.{instance_id()}.{component_name}"
