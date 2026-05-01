"""Топики и actions для DroneRegistry в составе drone_port."""

import os


_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    DRONE_REGISTRY = f"{_P}components.drone_registry"
    CHARGING_MANAGER = f"{_P}components.charging_manager"

    @classmethod
    def all(cls) -> list:
        return [
            cls.DRONE_REGISTRY,
            cls.CHARGING_MANAGER,
        ]


class DroneRegistryActions:
    REGISTER_DRONE = "register_drone"
    REMOVE_DRONE = "remove_drone"
    GET_AVAILABLE_DRONES = "get_available_drones"
    UPDATE_BATTERY = "update_battery"
    GET_DRONE = "get_drone"