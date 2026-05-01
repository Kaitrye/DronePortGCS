"""Gateway — внешний шлюз."""
from typing import Optional, Dict, Any

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent

from ..topics import ComponentTopics, GatewayActions, SystemTopics


class DronePortGateway(BaseComponent):
    PROXY_TIMEOUT = 10.0

    def __init__(
        self,
        system_id: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        super().__init__(
            component_id=system_id,
            component_type="drone_port",
            topic=SystemTopics.DRONE_PORT,
            bus=bus,
        )
        self.system_id = system_id
        self.health_port = health_port

    def _register_handlers(self) -> None:
        self.register_handler(GatewayActions.GET_AVAILABLE_DRONES, self._handle_get_available_drones)
        self.register_handler(GatewayActions.REQUEST_LANDING, self._handle_request_landing)
        self.register_handler(GatewayActions.REQUEST_TAKEOFF, self._handle_request_takeoff)

    def _handle_get_available_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получить список доступных дронов."""
        payload = message.get("payload", {})
        
        response = self.bus.request(
            ComponentTopics.DRONE_REGISTRY,
            {
                "action": GatewayActions.GET_AVAILABLE_DRONES,
                "sender": self.topic,
                "payload": payload,
            },
            timeout=self.PROXY_TIMEOUT,
        )
        
        if response is None:
            return {"error": "failed: get_available_drones"}
        
        # DroneRegistry возвращает {"drones": [...]}
        if isinstance(response, dict):
            if "drones" in response:
                return response
            if "error" in response:
                return {"error": response["error"]}
        
        return {"drones": []}

    def _handle_request_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запросить посадку."""
        payload = message.get("payload", {})
        
        response = self.bus.request(
            ComponentTopics.LANDING_MANAGER,
            {
                "action": GatewayActions.REQUEST_LANDING,
                "sender": self.topic,
                "payload": payload,
            },
            timeout=self.PROXY_TIMEOUT,
        )
        
        if response is None:
            return {"error": "failed: request_landing"}
        
        # LandingManager возвращает {"approved": True, "port_id": "...", "drone_id": "..."}
        if isinstance(response, dict):
            if "approved" in response:
                # Убираем 'from' если есть
                response.pop("from", None)
                return response
            if "error" in response:
                return {"error": response["error"]}
        
        return {"error": "invalid response from landing_manager"}

    def _handle_request_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запросить взлёт."""
        payload = message.get("payload", {})
        
        response = self.bus.request(
            ComponentTopics.TAKEOFF_MANAGER,
            {
                "action": GatewayActions.REQUEST_TAKEOFF,
                "sender": self.topic,
                "payload": payload,
            },
            timeout=self.PROXY_TIMEOUT,
        )
        
        if response is None:
            return {"error": "failed: request_takeoff"}
        
        # TakeoffManager возвращает {"approved": True, "drone_id": "...", "battery": ...}
        if isinstance(response, dict):
            if "approved" in response:
                # Убираем 'from' если есть
                response.pop("from", None)
                return response
            if "error" in response:
                return {"error": response["error"]}
        
        return {"error": "invalid response from takeoff_manager"}

    def start(self) -> None:
        """Запуск gateway."""
        super().start()
        # TODO: запустить health check сервер если health_port указан

    def stop(self) -> None:
        """Остановка gateway."""
        super().stop()