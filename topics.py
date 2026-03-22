"""Внешние топики и actions GCS для взаимодействия с дроном."""


class DroneTopics:
    DRONE = "drone"


class DroneActions:
    UPLOAD_MISSION = "drone.upload_mission"
    MISSION_START = "drone.mission.start"


__all__ = ["DroneTopics", "DroneActions"]
