"""Топики для TakeoffManager."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    TAKEOFF_MANAGER = f"{_P}components.takeoff_manager"
    PORT_MANAGER = f"{_P}components.port_manager"
    DRONE_REGISTRY = f"{_P}components.drone_registry"


class TakeoffManagerActions:
    REQUEST_TAKEOFF = "request_takeoff"      # от Gateway
    RELEASE_PORT = "release_port"            # вызов PortManager
    REMOVE_DRONE = "remove_drone"            # вызов DroneRegistry
    GET_DRONE = "get_drone"                  # вызов DroneRegistry (добавлено)