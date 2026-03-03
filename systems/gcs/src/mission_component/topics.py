"""Топики, actions и events для MissionComponent."""


class SystemTopics:
    GCS_MISSION = "systems.gcs.mission"
    GCS_ORCHESTRATOR = "systems.gcs.orchestrator"
    GCS_REDIS = "systems.gcs.redis"


class MissionActions:
    TASK_SUBMIT = "task.submit"
    MISSION_CANCEL = "mission.cancel"
    GET_MISSION = "mission.get"


class MissionEvents:
    MISSION_CREATED = "mission.created"
    MISSION_STARTED = "mission.started"
    MISSION_FAILED = "mission.failed"
    MISSION_CANCELLED = "mission.cancelled"
    MISSION_ABORTED = "mission.aborted"
