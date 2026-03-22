"""MissionConverterComponent конвертирует массив точек в WPL формат для отправки дронам."""

from __future__ import annotations

from typing import Any, Dict

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from sdk.wpl_generator_2 import points_to_wpl as points_to_wpl_v2
from systems.gcs.src.mission_converter.topics import ComponentTopics, MissionActions
from systems.gcs.src.mission_store.topics import MissionStoreActions


class MissionConverterComponent(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="gcs_mission_converter",
            topic=ComponentTopics.GCS_MISSION_CONVERTER,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(MissionActions.MISSION_PREPARE, self._handle_mission_prepare)

    def _handle_mission_prepare(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        correlation_id = message.get("correlation_id")

        mission_response = self.send_to_other_system(
            ComponentTopics.GCS_MISSION_STORE,
            MissionStoreActions.GET_MISSION,
            {
                "mission_id": mission_id
            },
            correlation_id=correlation_id,
        )

        if mission_response and mission_response.get("success"):
            mission_payload = mission_response.get("payload", {})
        else:
            return {
                "error": "mission store unavailable",
                "from": self.component_id,
            }

        mission = mission_payload.get("mission") or {}
        points = mission.get("waypoints")
        if not isinstance(points, list):
            points = []

        wpl = points_to_wpl_v2(points)

        return {
            "mission": {
                "mission_id": mission_id,
                "wpl": wpl,
            },
            "from": self.component_id,
        }
