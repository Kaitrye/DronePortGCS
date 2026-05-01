"""Топики и actions для PortManager в составе drone_port."""

import os


_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    PORT_MANAGER = f"{_P}components.port_manager"

    @classmethod
    def all(cls) -> list:
        return [
            cls.PORT_MANAGER,
        ]


class PortManagerActions:
    OCCUPY_PORT = "occupy_port"
    RELEASE_PORT = "release_port"
