"""Топики и actions для PortManager в составе drone_port."""

from systems.drone_port.src.topic_naming import build_component_topic


class ComponentTopics:
    PORT_MANAGER = build_component_topic("port_manager")
    STATE_STORE = build_component_topic("state_store")

    @classmethod
    def all(cls) -> list:
        return [
            cls.PORT_MANAGER,
            cls.STATE_STORE,
        ]


class PortManagerActions:
    REQUEST_LANDING = "request_landing"
    FREE_SLOT = "free_slot"
    GET_PORT_STATUS = "get_port_status"
