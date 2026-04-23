"""Security monitor for drone_port ingress and SITL egress."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set, Tuple

from broker.src.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.drone_port.src.drone_manager.topics import ComponentTopics as DroneManagerTopics
from systems.drone_port.src.orchestrator.topics import ComponentTopics as OrchestratorTopics
from systems.drone_port.src.security_monitor import config
from systems.drone_port.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions


PolicyKey = Tuple[str, str, str]

logger = logging.getLogger(__name__)


class SecurityMonitorComponent(BaseComponent):
    def __init__(
        self,
        component_id: str,
        bus: SystemBus,
        topic: str = "",
        policies: Optional[Set[PolicyKey]] = None,
    ):
        self._policies = set(policies) if policies is not None else config.load_policies_from_env()
        self._audit_topic = config.audit_topic()
        super().__init__(
            component_id=component_id,
            component_type="drone_port_security_monitor",
            topic=(topic or config.component_topic()),
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(SecurityMonitorActions.PROXY_REQUEST, self._handle_proxy_request)
        self.register_handler(SecurityMonitorActions.PROXY_PUBLISH, self._handle_proxy_publish)
        self.register_handler(SecurityMonitorActions.LIST_POLICIES, self._handle_list_policies)

    def _extract_target(self, payload: Dict[str, Any]) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        target = payload.get("target") or {}
        target_topic = str(target.get("topic", "")).strip()
        target_action = str(target.get("action", "")).strip()
        if not target_topic or not target_action:
            return None
        target_payload = payload.get("data", {})
        if not isinstance(target_payload, dict):
            return None
        return target_topic, target_action, target_payload

    def _is_allowed(self, sender_id: str, target_topic: str, target_action: str) -> bool:
        return (sender_id, target_topic, target_action) in self._policies

    def _audit(self, action: str, source: str, details: Dict[str, Any]) -> None:
        logger.info("[%s] %s source=%s details=%r", self.component_id, action, source, details)
        if not self._audit_topic:
            return

        self.bus.publish(
            self._audit_topic,
            {
                "action": action,
                "sender": self.topic,
                "payload": {
                    "source": source,
                    "details": details,
                },
            },
        )

    def _route_request(self, target_topic: str, target_action: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        timeout = config.proxy_request_timeout_s()
        if target_topic != ExternalTopics.DRONE_PORT:
            return None

        if target_action == "get_available_drones":
            bus_topic = OrchestratorTopics.ORCHESTRATOR
        elif target_action in {"request_landing", "request_takeoff"}:
            bus_topic = DroneManagerTopics.DRONE_MANAGER
        else:
            return None

        return self.bus.request(
            bus_topic,
            {
                "action": target_action,
                "sender": self.topic,
                "payload": data,
            },
            timeout=timeout,
        )

    def _route_publish(self, target_topic: str, target_action: str, data: Dict[str, Any]) -> bool:
        if target_topic == ExternalTopics.SITL and target_action == SecurityMonitorActions.SITL_HOME_PUBLISH:
            return self.bus.publish(ExternalTopics.SITL, dict(data))

        return False

    def _handle_proxy_request(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = message.get("payload") or {}
        sender_id = str(message.get("sender") or "").strip()
        target = self._extract_target(payload)
        if not sender_id or target is None:
            self._audit(
                action="drone_port.monitor.proxy_request.invalid",
                source=sender_id or "unknown",
                details={"reason": "invalid_target_or_sender", "message": message},
            )
            return None

        target_topic, target_action, target_payload = target
        if not self._is_allowed(sender_id, target_topic, target_action):
            self._audit(
                action="drone_port.monitor.proxy_request.denied",
                source=sender_id,
                details={
                    "target_topic": target_topic,
                    "target_action": target_action,
                },
            )
            return None

        response = self._route_request(target_topic, target_action, target_payload)
        if not isinstance(response, dict):
            self._audit(
                action="drone_port.monitor.proxy_request.no_response",
                source=sender_id,
                details={
                    "target_topic": target_topic,
                    "target_action": target_action,
                },
            )
            return None

        return {
            "target_topic": target_topic,
            "target_action": target_action,
            "target_response": response,
        }

    def _handle_proxy_publish(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = message.get("payload") or {}
        sender_id = str(message.get("sender") or "").strip()
        target = self._extract_target(payload)
        if not sender_id or target is None:
            return None

        target_topic, target_action, target_payload = target
        if not self._is_allowed(sender_id, target_topic, target_action):
            return None

        published = self._route_publish(target_topic, target_action, target_payload)
        return {"published": bool(published)}

    def _handle_list_policies(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        policies = [
            {"sender": sender, "topic": topic, "action": action}
            for sender, topic, action in sorted(self._policies)
        ]
        return {
            "count": len(policies),
            "policies": policies,
        }
