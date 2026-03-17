"""Топики, actions и events для OrchestratorComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_ORCHESTRATOR = build_component_topic("orchestrator")
    GCS_PATH_PLANNER = build_component_topic("path_planner")
    GCS_MISSION_CONVERTER = build_component_topic("mission_converter")
    GCS_DRONE_MANAGER = build_component_topic("drone_manager")
    GCS_DRONE_STORE = build_component_topic("drone_store")
    GCS_MISSION_STORE = build_component_topic("mission_store")


class OrchestratorActions:
    TASK_SUBMIT = "task.submit"
    TASK_ASSIGN = "task.assign"
    TASK_START = "task.start"
