"""OrchestratorComponent"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.gcs.src.orchestrator.topics import OrchestratorActions, ComponentTopics
from systems.gcs.src.path_planner.topics import PathPlannerActions


# Единая точка входа для команд эксплуатанта.
class OrchestratorComponent(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="gcs_orchestrator",
            topic=ComponentTopics.GCS_ORCHESTRATOR,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(OrchestratorActions.TASK_SUBMIT, self._handle_task_submit)
        self.register_handler(OrchestratorActions.TASK_AVAILABLE_DRONES, self._handle_task_available_drones)
        self.register_handler(OrchestratorActions.TASK_ASSIGN, self._handle_task_assign)
        self.register_handler(OrchestratorActions.TASK_START, self._handle_task_start)

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


    def _handle_task_submit(self, message: Dict[str, Any]) -> Dict[str, Any]:
        task_payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = f"m-{uuid4().hex[:12]}"

        planned = self.send_to_other_system(
            ComponentTopics.GCS_PATH_PLANNER,
            PathPlannerActions.PATH_PLAN,
            {
                "mission_id": mission_id, 
                "task": task_payload
            },
            correlation_id=correlation_id,
        )

        if planned and planned.get("success"):
            payload = planned.get("payload", {})
            waypoints = payload.get("waypoints", [])
            signature = payload.get("signature")

            if isinstance(waypoints, list) and len(waypoints) >= 4:
                return {
                    "from": self.component_id,
                    "mission_id": mission_id,
                    "waypoints": waypoints,
                    "signature": signature,
                }

        return {
            "from": self.component_id, 
            "error": "failed to build route"
        }

    def _handle_task_available_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        correlation_id = message.get("correlation_id")

        drones_response = self.send_to_other_system(
            ComponentTopics.GCS_DRONE_STORE,
            "store.available_drones",
            {},
            correlation_id=correlation_id,
        )

        if drones_response and drones_response.get("success"):
            payload = drones_response.get("payload", {})
            return {
                "from": self.component_id,
                "available_drones": payload.get("available_drones", []),
            }

        return {
            "from": self.component_id, 
            "error": "store unavailable"
        }


    def _handle_task_assign(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")

        prepared = self.send_to_other_system(
            ComponentTopics.GCS_MISSION_CONVERTER,
            "mission.prepare",
            {
                "mission_id": mission_id,
            },
            correlation_id=correlation_id,
        )

        if prepared and prepared.get("success"):
            prepared_payload = prepared.get("payload", {})
            prepared_mission = prepared_payload.get("mission", {})
            wpl = prepared_mission.get("wpl")

            if wpl:
                self.publish_to_other_system(
                    ComponentTopics.GCS_DRONE,
                    "mission.upload",
                    {
                        "mission_id": mission_id,
                        "drone_id": drone_id,
                        "wpl": wpl,
                    },
                    correlation_id=correlation_id,
                )

        return None


    def _handle_task_start(self, message: Dict[str, Any]) -> None:
        payload = message.get("payload", {})
        correlation_id = message.get("correlation_id")
        mission_id = payload.get("mission_id")
        drone_id = payload.get("drone_id")

        self.publish_to_other_system(
            ComponentTopics.GCS_DRONE,
            "mission.start",
            {
                "mission_id": mission_id, 
                "drone_id": drone_id
            },
            correlation_id=correlation_id,
        )

        return None
