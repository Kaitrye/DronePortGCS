"""Topics and actions for DroneStoreComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_DRONE_STORE = build_component_topic("drone_store")


class DroneStoreActions:
    AVAILABLE_DRONES = "store.available_drones"
    UPDATE_DRONE = "store.update_drone"
    SAVE_TELEMETRY = "telemetry.save"
