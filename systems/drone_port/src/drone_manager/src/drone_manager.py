"""
DroneManager — взаимодействие с физическими дронами (БВС).
Запросы самодиагностики + координация с портами.
"""
import datetime
from typing import Dict, Any, Optional, List
from sdk.base_component import BaseComponent
from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.drone_manager.topics import DroneManagerTopics
from systems.drone_port.src.drone_registry.topics import DroneRegistryTopics
from systems.drone_port.src.port_manager.topics import PortManagerTopics


class DroneManager(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: MQTTSystemBus,
    ):
        self.topics = DroneManagerTopics(component_id)
        self.registry_topics = DroneRegistryTopics(component_id)
        self.port_topics = PortManagerTopics(component_id)
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"DroneManager '{name}' initialized")
        
        # Локальный кэш позиций для SITL
        self._drone_positions: Dict[str, Dict[str, Any]] = {}
        
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрация обработчиков (только необходимые)."""
        # === Команды от дронов ===
        self.register_handler("request_landing", self._handle_request_landing)
        self.register_handler("request_takeoff", self._handle_request_takeoff)
        self.register_handler("self_diagnostics", self._handle_self_diagnostics)
        
        # === Запросы данных (одинаковый формат для SITL и Эксплуатанта) ===
        self.register_handler("get_available_drones", self._handle_get_available_drones)

    def _handle_request_landing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос разрешения на посадку от дрона."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        response = self.bus.request(
            self.port_topics.REQUEST_LANDING_SLOT,
            {"payload": {"drone_id": drone_id}},
            timeout=5.0
        )
        
        if response and response.get("status") == "slot_assigned":
            port_id = response.get("port_id")
            
            # ✅ Регистрация дрона происходит автоматически при посадке
            # (DroneRegistry подпишется на событие или запросит данные)
            
            self.bus.publish(
                self.topics.LANDING_ALLOWED,
                {"payload": {"drone_id": drone_id, "port_id": port_id}}
            )
            
            return {"payload": {"status": "landing_allowed", "port_id": port_id}}
        
        return {"payload": {"status": "landing_denied", "reason": "No available slots"}}

    def _handle_request_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос разрешения на взлёт от дрона."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        # ✅ Удаление дрона из реестра происходит автоматически при взлёте
        # (DroneRegistry подпишется на событие)
        
        self.bus.publish(
            self.port_topics.RELEASE_SLOT,
            {"payload": {"drone_id": drone_id}}
        )
        
        self.bus.publish(
            self.topics.TAKEOFF_ALLOWED,
            {"payload": {"drone_id": drone_id}}
        )
        
        return {"payload": {"status": "takeoff_allowed"}}

    def _handle_self_diagnostics(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка запроса самодиагностики от дрона."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        health_data = payload.get("health_data", {})
        
        # Отправка данных о здоровье в Registry (если нужно)
        if health_data:
            self.bus.publish(
                self.registry_topics.UPDATE_DRONE_STATE,
                {"payload": {"drone_id": drone_id, "health_data": health_data}}
            )
        
        return {"payload": {"status": "diagnostics_complete"}}

    def _handle_get_available_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Возвращает список доступных дронов с локацией.
        ✅ Один формат ответа для SITL и Эксплуатанта.
        ✅ Минимальный набор полей: lat, lon, alt, battery.
        ✅ Ответ: {"payload": {"drones": [...]}}
        """
        # Запрос списка дронов из DroneRegistry
        response = self.bus.request(
            self.registry_topics.LIST_DRONES,
            {"payload": {}},
            timeout=5.0
        )
        
        if not response:
            return {"payload": {"drones": []}}
        
        drones = response.get("payload", {}).get("drones", [])
        
        # Формируем минимальный ответ
        result = []
        for drone in drones:
            if drone.get("status") in ["landed", "ready", "charging"]:
                position = self._drone_positions.get(drone["drone_id"], {})
                
                result.append({
                    "drone_id": drone["drone_id"],
                    "status": drone.get("status"),
                    "battery_level": float(drone.get("battery_level", 0)),
                    "location": {
                        "lat": position.get("lat", 0.0),
                        "lon": position.get("lon", 0.0),
                        "alt": position.get("alt", 0.0)
                    }
                })
        
        return {"payload": {"drones": result}}

    def update_drone_position(self, drone_id: str, lat: float, lon: float, alt: float, battery: float) -> None:
        """
        Обновляет позицию дрона в локальном кэше.
        Вызывается при получении телеметрии (не через handler).
        """
        self._drone_positions[drone_id] = {
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "battery": battery,
            "last_update": datetime.datetime.utcnow().isoformat()
        }