"""PathPlanner с заглушкой построения маршрута."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.gcs.src.contracts import MissionStatus
from systems.gcs.src.path_planner.topics import ComponentTopics, PathPlannerActions


class PathPlannerComponent(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="gcs_path_planner",
            topic=ComponentTopics.GCS_PATH_PLANNER,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(PathPlannerActions.PATH_PLAN, self._handle_path_plan)

    def send_to_other_system(
        self,
        target_topic: str,
        action: str,
        payload: dict,
        timeout: float = 10.0,
        correlation_id: Optional[str] = None,
    ) -> Optional[dict]:
        request_message = {
            "action": action,
            "sender": self.component_id,
            "payload": payload,
        }
        if correlation_id:
            request_message["correlation_id"] = correlation_id

        return self.bus.request(
            target_topic,
            request_message,
            timeout=timeout,
        )

    def publish_to_other_system(
        self,
        target_topic: str,
        action: str,
        payload: dict,
        correlation_id: Optional[str] = None,
    ) -> None:
        message = {
            "action": action,
            "sender": self.component_id,
            "payload": payload,
        }
        if correlation_id:
            message["correlation_id"] = correlation_id

        self.bus.publish(target_topic, message)

    @staticmethod
    def _normalize_point(raw_point: Any) -> Optional[Dict[str, float]]:
        if not isinstance(raw_point, dict):
            return None

        lat = raw_point.get("lat", raw_point.get("latitude"))
        lon = raw_point.get("lon", raw_point.get("lng", raw_point.get("longitude")))
        alt = raw_point.get("alt", raw_point.get("altitude", 0.0))

        if lat is None or lon is None:
            return None

        try:
            return {
                "lat": float(lat),
                "lon": float(lon),
                "alt": float(alt),
            }
        except (TypeError, ValueError):
            return None

    @classmethod
    def _extract_start_end(cls, task: Dict[str, Any]) -> tuple[Optional[Dict[str, float]], Optional[Dict[str, float]]]:
        start_point = cls._normalize_point(task.get("start_point"))
        end_point = cls._normalize_point(task.get("end_point"))
        return start_point, end_point

    @staticmethod
    def _interpolate(a: Dict[str, float], b: Dict[str, float], ratio: float) -> Dict[str, float]:
        return {
            "lat": a["lat"] + (b["lat"] - a["lat"]) * ratio,
            "lon": a["lon"] + (b["lon"] - a["lon"]) * ratio,
            "alt": a["alt"] + (b["alt"] - a["alt"]) * ratio,
        }

    @classmethod
    def _build_stub_route(cls, start_point: Dict[str, float], end_point: Dict[str, float]) -> list[Dict[str, float]]:
        out_mid_1 = cls._interpolate(start_point, end_point, 0.33)
        out_mid_2 = cls._interpolate(start_point, end_point, 0.66)
        back_mid_1 = cls._interpolate(end_point, start_point, 0.33)
        back_mid_2 = cls._interpolate(end_point, start_point, 0.66)

        # Заглушка: маршрут туда и обратно с промежуточными точками.
        return [
            start_point,
            out_mid_1,
            out_mid_2,
            end_point,
            back_mid_1,
            back_mid_2,
            start_point,
        ]

    def _handle_path_plan(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload")
        mission_id = payload.get("mission_id")
        task = payload.get("task")
        correlation_id = message.get("correlation_id")

        start_point, end_point = self._extract_start_end(task)

        waypoints = self._build_stub_route(start_point, end_point)
        now = datetime.now(timezone.utc).isoformat()
        signature = hashlib.sha256(
            json.dumps(waypoints, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        self.publish_to_other_system(
            ComponentTopics.GCS_MISSION_STORE,
            "store.save_mission",
            {
                "mission": {
                    "mission_id": mission_id,
                    "waypoints": waypoints,
                    "signature": signature,
                    "status": MissionStatus().CREATED,
                    "assigned_drone": None,
                    "created_at": now,
                    "updated_at": now,
                }
            },
            correlation_id=correlation_id,
        )

        return {
            "from": self.component_id,
            "mission_id": mission_id,
            "waypoints": waypoints,
            "signature": signature,
        }
