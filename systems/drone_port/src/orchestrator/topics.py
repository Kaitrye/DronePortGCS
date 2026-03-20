"""Топики и actions для Orchestrator в составе drone_port."""

from systems.drone_port.src.topic_naming import build_component_topic


class ComponentTopics:
    ORCHESTRATOR = build_component_topic("orchestrator")
    DRONE_REGISTRY = build_component_topic("registry")

    @classmethod
    def all(cls) -> list:
        return [
            cls.ORCHESTRATOR,
            cls.DRONE_REGISTRY,
        ]


class OrchestratorActions:
    GET_AVAILABLE_DRONES = "get_available_drones"
