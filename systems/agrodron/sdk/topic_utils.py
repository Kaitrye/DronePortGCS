from __future__ import annotations

from sdk.topic_naming import clean_topic_part, instance_id as base_instance_id
from sdk.topic_naming import system_name as base_system_name
from sdk.topic_naming import topic_version


def system_name(default: str = "Agrodron") -> str:
    return base_system_name("SYSTEM_NAME", default)


def instance_id(default: str = "Agrodron001") -> str:
    return base_instance_id("INSTANCE_ID", default)


def topic_prefix() -> str:
    return ".".join([topic_version(), system_name(), instance_id()])


def topic_for(component: str) -> str:
    return ".".join([topic_prefix(), clean_topic_part(component)])
