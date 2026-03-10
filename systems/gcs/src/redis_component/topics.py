"""Топики, actions и events для RedisComponent."""


class SystemTopics:
    GCS_REDIS = "systems.gcs.redis"


class RedisActions:
    SAVE_MISSION = "redis.save_mission"
    GET_MISSION = "redis.get_mission"
    UPDATE_MISSION = "redis.update_mission"
    UPSERT_TELEMETRY = "redis.upsert_telemetry"
    ALLOCATE_DRONES = "redis.allocate_drones"
    RELEASE_DRONES = "redis.release_drones"
    GET_FLEET_STATUS = "redis.get_fleet_status"


class RedisEvents:
    MISSION_SAVED = "redis.mission.saved"
    FLEET_UPDATED = "redis.fleet.updated"
    TELEMETRY_UPDATED = "redis.telemetry.updated"
