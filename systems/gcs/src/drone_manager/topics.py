"""Топики, actions и events для DroneManagerComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_DRONE = build_component_topic("drone_manager")
    GCS_MISSION_STORE = build_component_topic("mission_store")
    GCS_DRONE_STORE = build_component_topic("drone_store")


class DroneManagerActions:
    MISSION_UPLOAD = "mission.upload"
    MISSION_START = "mission.start"
    TELEMETRY_SAVE = "telemetry.save"
