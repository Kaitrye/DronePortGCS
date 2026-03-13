"""Topics and actions for MissionStoreComponent."""

from systems.gcs.src.topic_naming import build_component_topic


class ComponentTopics:
    GCS_MISSION_STORE = build_component_topic("mission_store")


class MissionStoreActions:
    SAVE_MISSION = "store.save_mission"
    GET_MISSION = "store.get_mission"
    UPDATE_MISSION = "store.update_mission"
