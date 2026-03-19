"""Топики и actions для StateStore в составе drone_port."""

from systems.drone_port.src.topic_naming import build_component_topic


class ComponentTopics:
    STATE_STORE = build_component_topic("state_store")

    @classmethod
    def all(cls) -> list:
        return [
            cls.STATE_STORE,
        ]


class StateStoreActions:
    GET_ALL_PORTS = "get_all_ports"
    UPDATE_PORT = "update_port"
