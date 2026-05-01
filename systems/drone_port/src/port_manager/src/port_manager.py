"""PortManager — управление посадочными слотами."""
import logging
from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.src.system_bus import SystemBus

from ..topics import ComponentTopics, PortManagerActions

logger = logging.getLogger(__name__)


class PortManager(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus):
        # Инициализируем _ports ДО вызова super().__init__
        # потому что super() вызовет _register_handlers
        self._ports: Dict[str, Dict] = {}
        self._seed_ports()
        
        super().__init__(
            component_id=component_id,
            component_type="drone_port",
            topic=ComponentTopics.PORT_MANAGER,
            bus=bus,
        )
        self.name = name

    def _seed_ports(self) -> None:
        """Инициализация портов."""
        if not self._ports:
            self._ports = {
                "P-01": {"port_id": "P-01", "drone_id": None, "status": "free"},
                "P-02": {"port_id": "P-02", "drone_id": None, "status": "free"},
                "P-03": {"port_id": "P-03", "drone_id": None, "status": "free"},
                "P-04": {"port_id": "P-04", "drone_id": None, "status": "free"},
            }
            logger.info("[%s] Initialized 4 ports", self.component_id if hasattr(self, 'component_id') else "port_manager")

    def _register_handlers(self) -> None:
        """Регистрация обработчиков."""
        self.register_handler(PortManagerActions.OCCUPY_PORT, self._handle_occupy_port)
        self.register_handler(PortManagerActions.RELEASE_PORT, self._handle_release_port)

    def _handle_occupy_port(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Резервирование порта для дрона."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")

        if not drone_id:
            return {"error": "drone_id required"}

        for port_id, port in self._ports.items():
            if port["status"] == "free" and port["drone_id"] is None:
                port["drone_id"] = drone_id
                port["status"] = "occupied"
                logger.info("[%s] Occupied port %s for drone %s", self.component_id, port_id, drone_id)
                return {"port_id": port_id}

        logger.warning("[%s] No free ports for drone %s", self.component_id, drone_id)
        return {"error": "No free ports"}

    def _handle_release_port(self, message: Dict[str, Any]) -> None:
        """Освобождение порта."""
        payload = message.get("payload", {})
        port_id = payload.get("port_id")
        drone_id = payload.get("drone_id")

        if not port_id or port_id not in self._ports:
            logger.warning("[%s] Invalid port_id %s for release", self.component_id, port_id)
            return

        self._ports[port_id]["drone_id"] = None
        self._ports[port_id]["status"] = "free"
        logger.info("[%s] Released port %s from drone %s", self.component_id, port_id, drone_id)