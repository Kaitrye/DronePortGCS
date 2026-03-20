"""Топики и actions для ChargingManager в составе drone_port"""

from systems.drone_port.src.topic_naming import build_component_topic


class ComponentTopics:
    CHARGING_MANAGER = build_component_topic("charging_manager")
    DRONE_REGISTRY = build_component_topic("registry")

    @classmethod
    def all(cls) -> list:
        return [
            cls.CHARGING_MANAGER,
            cls.DRONE_REGISTRY,
        ]


class ChargingManagerActions:
    START_CHARGING = "start_charging"
    GET_CHARGING_STATUS = "get_charging_status"
