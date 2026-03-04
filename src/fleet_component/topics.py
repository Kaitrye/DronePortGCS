"""Топики, actions и events для FleetComponent."""


class SystemTopics:
    GCS_FLEET = "systems.gcs.fleet"
    GCS_REDIS = "systems.gcs.redis"


class FleetActions:
    ALLOCATE = "fleet.allocate"
    RELEASE = "fleet.release"
    GET_STATUS = "fleet.get_status"


class FleetEvents:
    DRONE_STATUS_CHANGED = "fleet.drone.status.changed"
    DRONE_BATTERY_LOW = "fleet.drone.battery.low"
    DRONE_UNAVAILABLE = "fleet.drone.unavailable"
