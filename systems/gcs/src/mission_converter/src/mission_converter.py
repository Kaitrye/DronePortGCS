"""MissionConverterComponent конвертирует массив точек в WPL формат для отправки дронам."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
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

    @staticmethod
    def _extract_points(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        if isinstance(payload.get("waypoints"), list):
            return payload["waypoints"]
        return []

    @staticmethod
    def _to_wpl(points: list[Dict[str, Any]]) -> str:
        lines = ["QGC WPL 110"]
        for idx, point in enumerate(points):
            lat = point.get("lat", point.get("latitude", 0.0))
            lon = point.get("lon", point.get("lng", point.get("longitude", 0.0)))
            alt = point.get("alt", point.get("altitude", 0.0))
            params = point.get("params", {})

            line = "\t".join(
                [
                    str(idx),
                    "1" if idx == 0 else "0",
                    str(point.get("frame", 3)),
                    str(point.get("command", 16)),
                    str(params.get("p1", 0)),
                    str(params.get("p2", 0)),
                    str(params.get("p3", 0)),
                    str(params.get("p4", 0)),
                    str(lat),
                    str(lon),
                    str(alt),
                    "1",
                ]
            )
            lines.append(line)

        return "\n".join(lines)

    def _handle_mission_prepare(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")

        mission_response = self.send_to_other_system(
            ComponentTopics.GCS_MISSION_STORE,
            MissionStoreActions.GET_MISSION,
            {
                "mission_id": mission_id
            },
        )

        if mission_response and mission_response.get("success"):
            mission_payload = mission_response.get("payload", {})
        else:
            return {
                "mission_id": mission_id, 
                "error": "mission store unavailable"
            }

        mission = mission_payload.get("mission")
        points = self._extract_points(mission)

        wpl = self._to_wpl(points)
        signature = hashlib.sha256(wpl.encode("utf-8")).hexdigest()

        return {
            "mission": {
                "mission_id": mission_id,
                "wpl": wpl,
                "signature": signature,
            }
        }
