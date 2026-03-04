"""Контракты доменной модели для GCS."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionStatus:
    CREATED: str = "created"
    PLANNED: str = "planned"
    RUNNING: str = "running"
    FAILED: str = "failed"
    CANCELLED: str = "cancelled"
    ABORTED: str = "aborted"
