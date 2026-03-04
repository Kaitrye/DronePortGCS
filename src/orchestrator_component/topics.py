"""Топики, actions и events для OrchestratorComponent."""


class SystemTopics:
    GCS_ORCHESTRATOR = "systems.gcs.orchestrator"
    GCS_FLEET = "systems.gcs.fleet"
    GCS_ROBOT = "systems.gcs.robot"
    GCS_REDIS = "systems.gcs.redis"


class OrchestratorActions:
    PLAN = "orchestrator.plan"
    CANCEL = "orchestrator.cancel"


class OrchestratorEvents:
    GROUP_FORMED = "orchestrator.group.formed"
