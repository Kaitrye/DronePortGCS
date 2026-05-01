"""Топики и внешние actions для gateway DronePort."""

import os


_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class SystemTopics:
    DRONE_PORT = f"{_P}systems.drone_port"


class ComponentTopics:
    GATEWAY = f"{_P}components.gateway"
    LANDING_MANAGER = f"{_P}components.takeoff_manager"
    DRONE_REGISTRY = f"{_P}components.drone_registry"
    TAKEOFF_MANAGER = f"{_P}components.takeoff_manager"

    @classmethod
    def all(cls) -> list:
        return [
            cls.GATEWAY,
            cls.LANDING_MANAGER,
            cls.DRONE_REGISTRY,
            cls.TAKEOFF_MANAGER
        ]


class GatewayActions:
    GET_AVAILABLE_DRONES = "get_available_drones"
    REQUEST_LANDING = "request_landing"
    REQUEST_TAKEOFF = "request_takeoff"
