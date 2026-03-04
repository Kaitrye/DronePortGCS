"""Топики, actions и events для TelemetryComponent."""


class SystemTopics:
    GCS_TELEMETRY = "systems.gcs.telemetry"
    GCS_REDIS = "systems.gcs.redis"


class TelemetryActions:
    TELEMETRY_UPDATE = "telemetry.update"


class TelemetryEvents:
    ANOMALY_DETECTED = "telemetry.anomaly.detected"
    DRONE_OFFLINE = "telemetry.drone.offline"
