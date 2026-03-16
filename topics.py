"""Совместимость: внешние топики drone переэкспортируются из общего модуля GCS."""

from systems.gcs.src.topics import ExternalDroneActions as DroneActions
from systems.gcs.src.topics import ExternalTopics as DroneTopics

__all__ = ["DroneTopics", "DroneActions"]
