"""Топики и actions для PathPlannerComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_PATH_PLANNER = build_component_topic("path_planner")
    GCS_MISSION_STORE = build_component_topic("mission_store")


class PathPlannerActions:
    PATH_PLAN = "path.plan"
