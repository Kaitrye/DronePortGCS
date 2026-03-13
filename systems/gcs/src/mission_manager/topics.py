"""Топики и actions для MissionConverterComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_MISSION_CONVERTER = build_component_topic("mission_converter")
    GCS_MISSION_STORE = build_component_topic("mission_store")


class MissionActions:
    MISSION_PREPARE = "mission.prepare"