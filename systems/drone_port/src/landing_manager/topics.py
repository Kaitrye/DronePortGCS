"""Топики для LandingManager."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    LANDING_MANAGER = f"{_P}components.landing_manager"
    PORT_MANAGER = f"{_P}components.port_manager"
    DRONE_REGISTRY = f"{_P}components.drone_registry"
    CHARGING_MANAGER = f"{_P}components.charging_manager"


class LandingManagerActions:
    REQUEST_LANDING = "request_landing"
    START_CHARGING = "start_charging"
    OCCUPY_PORT = "occupy_port"
    REGISTER_DRONE = "registed_drone"