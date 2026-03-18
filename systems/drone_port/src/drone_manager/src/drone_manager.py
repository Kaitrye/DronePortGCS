"""
DroneManager — взаимодействие с физическими дронами.
"""
import datetime
from typing import Dict, Any
from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.drone_port.src.drone_manager.topics import DroneManagerTopics


class DroneManager(BaseComponent):
    """
    Передает запросы:
    - от дронов к PortManager (landing/takeoff)
    - от дронов к ChargingManager (charging)
    - от Registry к дронам (через события)
    """
    
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.topics = DroneManagerTopics(component_id)
        
        self._drone_locations: Dict[str, str] = {}  # drone_id -> port_id
        self._drone_battery: Dict[str, float] = {}  # drone_id -> battery_level
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"DroneManager '{name}' initialized")

    def _register_handlers(self) -> None:
        self.register_handler("request_landing", self._handle_landing)
        self.register_handler("request_takeoff", self._handle_takeoff)
        self.register_handler("request_charging", self._handle_charging)  # новый
        self.register_handler("get_available_drones", self._handle_get_available)

    def _handle_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на посадку от дрона.
        
        Принимает:
            drone_id: ID дрона
            battery: текущий заряд батареи (опционально)
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        battery = payload.get("battery", 100.0)
        
        if not drone_id:
            return {"status": "error", "reason": "No drone_id"}
        
        # Запоминаем уровень батареи
        self._drone_battery[drone_id] = float(battery)
        
        # Спрашиваем PortManager
        response = self.bus.request(
            "v1.droneport.dp-001.port_manager.request_landing_slot",
            {"payload": {"drone_id": drone_id}},
            timeout=3.0
        )
        
        if not response or response.get("status") != "slot_assigned":
            return {
                "status": "denied",
                "reason": "No free slots"
            }
        
        port_id = response.get("port_id")
        
        # Запоминаем, куда сел
        self._drone_locations[drone_id] = port_id
        
        # Сообщаем дрону
        self.bus.publish(
            self.topics.LANDING_ALLOWED,
            {
                "event": "landing_allowed",
                "drone_id": drone_id,
                "port_id": port_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return {
            "status": "allowed",
            "port_id": port_id
        }

    def _handle_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на взлет от дрона.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {"status": "error", "reason": "No drone_id"}
        
        if drone_id not in self._drone_locations:
            return {"status": "error", "reason": "Drone not on ground"}
        
        port_id = self._drone_locations[drone_id]
        
        # Говорим PortManager освободить слот
        self.bus.request(
            "v1.droneport.dp-001.port_manager.release_slot",
            {"payload": {"drone_id": drone_id, "port_id": port_id}},
            timeout=2.0
        )
        
        # Удаляем из памяти
        del self._drone_locations[drone_id]
        if drone_id in self._drone_battery:
            del self._drone_battery[drone_id]
        
        # Сообщаем дрону
        self.bus.publish(
            self.topics.TAKEOFF_ALLOWED,
            {
                "event": "takeoff_allowed",
                "drone_id": drone_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return {"status": "allowed"}

    def _handle_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос на зарядку от дрона.
        
        Дрон может сам запросить зарядку, если у него низкий заряд.
        
        Принимает:
            drone_id: ID дрона
            target_battery: целевой уровень зарядки (опционально)
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {"status": "error", "reason": "No drone_id"}
        
        # Проверяем, что дрон на земле
        if drone_id not in self._drone_locations:
            return {
                "status": "error", 
                "reason": "Drone not on ground - cannot charge in air"
            }
        
        port_id = self._drone_locations[drone_id]
        current_battery = self._drone_battery.get(drone_id, 0)
        
        # Отправляем запрос в ChargingManager через Registry
        # (согласно схеме: drone_manager -> registry -> charging_manager)
        response = self.bus.request(
            "v1.droneport.dp-001.registry.start_charging",
            {
                "payload": {
                    "drone_id": drone_id,
                    "port_id": port_id,
                    "current_battery": current_battery,
                    "target_battery": payload.get("target_battery", 100.0)
                }
            },
            timeout=5.0
        )
        
        if not response:
            return {
                "status": "error",
                "reason": "Charging service unavailable"
            }
        
        # Публикуем событие о запросе зарядки
        self.bus.publish(
            self.topics.CHARGING_REQUESTED,
            {
                "event": "charging_requested",
                "drone_id": drone_id,
                "port_id": port_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return response

    def _handle_get_available(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Список дронов на земле, готовых к вылету.
        """
        available = []
        for drone_id, port_id in self._drone_locations.items():
            battery = self._drone_battery.get(drone_id, 100.0)
            available.append({
                "drone_id": drone_id,
                "port_id": port_id,
                "battery": battery,
                "status": "ready" if battery > 20 else "low_battery"
            })
        
        # Если никого нет - возвращаем тестовые данные
        if not available:
            available = [
                {"drone_id": "DR-001", "port_id": "P-01", "battery": 95, "status": "ready"},
                {"drone_id": "DR-002", "port_id": "P-02", "battery": 87, "status": "ready"},
                {"drone_id": "DR-003", "port_id": "P-03", "battery": 15, "status": "low_battery"},
            ]
        
        return {
            "status": "success",
            "payload": {"drones": available}
        }