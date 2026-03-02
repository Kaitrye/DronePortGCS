"""Топики и actions для DummyComponent в составе dummy_system."""


class ComponentTopics:
    DUMMY_COMPONENT_A = "components.gcs_comp_a"
    DUMMY_COMPONENT_B = "components.gcs_comp_b"

    @classmethod
    def all(cls) -> list:
        return [cls.DUMMY_COMPONENT_A, cls.DUMMY_COMPONENT_B]


class DummyComponentActions:

