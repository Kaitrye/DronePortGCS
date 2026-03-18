"""
PortManager — управление посадочными площадками.
"""
import datetime
from typing import Dict, Any, List
from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.drone_port.src.port_manager.topics import PortManagerTopics


class PortManager(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.topics = PortManagerTopics(component_id)
        
        self._ports = {
            "P-01": {"drone_id": None, "status": "free"},
            "P-02": {"drone_id": None, "status": "free"},
            "P-03": {"drone_id": None, "status": "free"},
            "P-04": {"drone_id": None, "status": "free"},
        }
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"PortManager '{name}' initialized")

    def _register_handlers(self) -> None:
        self.register_handler("reserve_slot", self._handle_reserve)
        self.register_handler("release_slot", self._handle_release)
        self.register_handler("request_landing_slot", self._handle_request_landing)
        self.register_handler("get_port_status", self._handle_get_status)

    def _handle_reserve(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Зарезервировать конкретный порт."""
        payload = message.get("payload", {})
        port_id = payload.get("port_id")
        drone_id = payload.get("drone_id")
        
        if not port_id or not drone_id:
            return {"status": "error", "reason": "Missing port_id or drone_id"}
        
        if port_id not in self._ports:
            return {"status": "error", "reason": f"Port {port_id} not found"}
        
        if self._ports[port_id]["drone_id"] is not None:
            return {"status": "error", "reason": "Port already occupied"}
        
        self._ports[port_id] = {"drone_id": drone_id, "status": "occupied"}
        
        return {"status": "reserved", "port_id": port_id, "drone_id": drone_id}

    def _handle_release(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Освободить порт."""
        payload = message.get("payload", {})
        port_id = payload.get("port_id")
        drone_id = payload.get("drone_id")
        
        if port_id:
            if port_id in self._ports:
                self._ports[port_id] = {"drone_id": None, "status": "free"}
                return {"status": "released", "port_id": port_id}
        
        # Если нет port_id, ищем по drone_id
        if drone_id:
            for pid, data in self._ports.items():
                if data.get("drone_id") == drone_id:
                    self._ports[pid] = {"drone_id": None, "status": "free"}
                    return {"status": "released", "port_id": pid}
        
        return {"status": "error", "reason": "Port or drone not found"}

    def _handle_request_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {"status": "error", "reason": "No drone_id"}
        
        # Ищем свободный порт
        for port_id, data in self._ports.items():
            if data["drone_id"] is None:
                # Занимаем порт
                self._ports[port_id] = {"drone_id": drone_id, "status": "occupied"}
                
                # Публикуем событие
                self.bus.publish(
                    self.topics.SLOT_ASSIGNED,
                    {
                        "event": "slot_assigned",
                        "port_id": port_id,
                        "drone_id": drone_id,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                )
                
                return {
                    "status": "slot_assigned",
                    "port_id": port_id
                }
        
        # Свободных портов нет
        return {
            "status": "denied",
            "reason": "No free slots"
        }

    def _handle_get_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Статус всех портов."""
        ports_list = []
        for port_id, data in self._ports.items():
            ports_list.append({
                "port_id": port_id,
                "drone_id": data["drone_id"],
                "status": data["status"]
            })
        
        return {
            "status": "success",
            "payload": ports_list
        }