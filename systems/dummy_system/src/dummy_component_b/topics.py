"""Топики и actions для DummyComponent в составе dummy_system."""


class ComponentTopics:
    DUMMY_COMPONENT_A = "components.dummy_component_a"
    DUMMY_COMPONENT_B = "components.dummy_component_b"

    @classmethod
    def all(cls) -> list:
        return [cls.DUMMY_COMPONENT_A, cls.DUMMY_COMPONENT_B]


class DummyComponentActions:
    ECHO = "echo"
    INCREMENT = "increment"
    GET_STATE = "get_state"
    ASK_B = "ask_b"
    GET_DATA = "get_data"
