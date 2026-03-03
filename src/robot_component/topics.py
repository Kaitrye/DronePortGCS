"""Топики, actions и events для RobotComponent."""


class SystemTopics:
    GCS_ROBOT = "systems.gcs.robot"
    GCS_FLEET = "systems.gcs.fleet"
    GCS_REDIS = "systems.gcs.redis"


class RobotActions:
    EXECUTE_MISSION = "robot.execute_mission"
    ABORT_MISSION = "robot.abort_mission"


class RobotEvents:
    STATE_CHANGED = "robot.state.changed"
    ERROR = "robot.error"


class ExternalTopics:
    DRONE_SERVICE = "external.drone_service"
    DRONEPORT = "systems.droneport"


class DroneServiceActions:
    UPLOAD_MISSION = "upload_mission"
    ARM = "arm"
    TAKEOFF = "takeoff"
    ABORT = "abort"


class DronePortActions:
    RESERVE_SLOTS = "reserve_slots"
    PREFLIGHT_CHECK = "preflight_check"
    CHARGE_TO_THRESHOLD = "charge_to_threshold"
    RELEASE_FOR_TAKEOFF = "release_for_takeoff"
    EMERGENCY_RECEIVE = "emergency_receive"
