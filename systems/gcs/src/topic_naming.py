"""Utilities for versioned, instance-safe topic naming in GCS."""

from __future__ import annotations

import os


def _clean(value: str) -> str:
    return (value or "").strip().replace("/", ".")


def topic_version() -> str:
    return _clean(os.getenv("TOPIC_VERSION", "v1")) or "v1"


def gcs_system_name() -> str:
    return _clean(os.getenv("GCS_SYSTEM_NAME", "gcs")) or "gcs"


def gcs_instance_id() -> str:
    return _clean(os.getenv("INSTANCE_ID", "1")) or "1"


def build_component_topic(component: str) -> str:
    component_name = _clean(component)
    return f"{topic_version()}.{gcs_system_name()}.{gcs_instance_id()}.{component_name}"
