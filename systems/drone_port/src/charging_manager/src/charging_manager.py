"""
ChargingManager — логика зарядки дронов.
"""
import datetime
from typing import Dict, Any, Optional
from sdk.base_component import BaseComponent
from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.charging_manager.topics import ChargingManagerTopics
from systems.drone_port.src.drone_registry.topics import DroneRegistryTopics


class ChargingManager(BaseComponent):
    def __init__(
        self,
        component_id: str,
        name: str,
        bus: MQTTSystemBus,
    ):
        self.topics = ChargingManagerTopics(component_id)
        self.registry_topics = DroneRegistryTopics(component_id)
        
        # ✅ Убран StateStore! Все данные через Broker → DroneRegistry
        self._local_cache: Dict[str, Dict[str, Any]] = {}  # Временный кэш для заглушки
        
        super().__init__(
            component_id=component_id,
            component_type="droneport",
            topic=self.topics.base_topic,
            bus=bus,
        )
        self.name = name
        print(f"ChargingManager '{name}' initialized (no direct StateStore access)")

    def _register_handlers(self) -> None:
        """Регистрация обработчиков по action (строка), не по топику!"""
        self.register_handler("start_charging", self._handle_start_charging)
        self.register_handler("stop_charging", self._handle_stop_charging)
        self.register_handler("charge_to_threshold", self._handle_charge_to_threshold)
        self.register_handler("get_charging_status", self._handle_get_charging_status)

    def _get_drone_from_registry(self, drone_id: str) -> Optional[Dict[str, Any]]:
        """
        ✅ Запрос данных о дроне из DroneRegistry через Broker.
        Временно используется локальный кэш как заглушка.
        """
        # === ЗАГЛУШКА: В будущем заменить на request к DroneRegistry ===
        # response = self.bus.request(
        #     self.registry_topics.GET_DRONE,
        #     {"action": "get_drone", "payload": {"drone_id": drone_id}},
        #     timeout=5.0
        # )
        # if response and response.get("status") == "ok":
        #     return response.get("drone")
        
        # Временная заглушка
        return self._local_cache.get(drone_id)

    def _save_drone_to_registry(self, drone_id: str, data: Dict[str, Any]) -> bool:
        """
        ✅ Обновление данных о дроне в DroneRegistry через Broker.
        Временно используется локальный кэш как заглушка.
        """
        # === ЗАГЛУШКА: В будущем заменить на request к DroneRegistry ===
        # response = self.bus.request(
        #     self.registry_topics.UPDATE_DRONE_STATE,
        #     {
        #         "action": "update_state",
        #         "payload": {"drone_id": drone_id, **data}
        #     },
        #     timeout=5.0
        # )
        # return response and response.get("status") == "updated"
        
        # Временная заглушка
        if drone_id in self._local_cache:
            self._local_cache[drone_id].update(data)
        else:
            self._local_cache[drone_id] = {
                "drone_id": drone_id,
                "status": "landed",
                "battery_level": "100.0",
                **data
            }
        return True

    def _handle_start_charging(self, message: Dict[str, Any]) -> None:
        """
        Обработка команды на запуск зарядки.
        ✅ Publish-only: не отправляет ответ обратно.
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            print(f"[{self.component_id}] No drone_id in payload")
            return
        
        # ✅ Запрос данных из DroneRegistry (через заглушку)
        drone = self._get_drone_from_registry(drone_id)
        if not drone:
            print(f"[{self.component_id}] Drone not found: {drone_id}")
            return
        
        # Обновление статуса
        update_data = {
            "status": "charging",
            "charging_started": datetime.datetime.utcnow().isoformat()
        }
        self._save_drone_to_registry(drone_id, update_data)
        
        # ✅ Публикация события о начале зарядки
        self.bus.publish(
            self.topics.CHARGING_STARTED,
            {
                "action": "charging_started",
                "drone_id": drone_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        print(f"[{self.component_id}] Charging started for drone: {drone_id}")
        # ✅ Не возвращаем ответ (publish-only)

    def _handle_stop_charging(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Остановка зарядки дрона."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        
        if not drone_id:
            return {"status": "failed", "reason": "No drone_id"}
        
        drone = self._get_drone_from_registry(drone_id)
        if drone:
            update_data = {
                "status": "landed",
                "charging_completed": datetime.datetime.utcnow().isoformat()
            }
            self._save_drone_to_registry(drone_id, update_data)
        
        self.bus.publish(
            self.topics.CHARGING_COMPLETED,
            {
                "action": "charging_completed",
                "drone_id": drone_id,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )
        
        return {"status": "charging_stopped", "drone_id": drone_id}

    def _handle_charge_to_threshold(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Зарядка до целевого уровня батареи."""
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        min_battery = float(payload.get("min_battery", 90.0))
        current_battery = float(payload.get("current_battery", 50.0))
        departure_time_sec = payload.get("departure_time_sec", 3600)
        
        if not drone_id:
            return {"status": "failed", "reason": "No drone_id"}
        
        if current_battery >= min_battery:
            return {
                "status": "charge.not_required",
                "drone_id": drone_id,
                "battery_level": current_battery
            }
        
        delta_bat = min_battery - current_battery
        required_energy_wh = delta_bat * 0.1
        max_power_w = 500.0
        charging_power_w = min(max_power_w, required_energy_wh * 3600 / departure_time_sec)
        
        update_data = {
            "charging_power_w": str(charging_power_w),
            "target_battery": str(min_battery),
            "status": "charging"
        }
        self._save_drone_to_registry(drone_id, update_data)
        
        # ✅ Уведомление DroneRegistry об обновлении
        self.bus.publish(
            self.registry_topics.UPDATE_DRONE_STATE,
            {
                "action": "update_state",
                "payload": {
                    "drone_id": drone_id,
                    "battery_level": str(min_battery),
                    "charging_power_w": str(charging_power_w)
                }
            }
        )
        
        return {
            "status": "charge.completed",
            "drone_id": drone_id,
            "charging_power_w": charging_power_w,
            "estimated_finish_sec": int(required_energy_wh * 3600 / charging_power_w) if charging_power_w > 0 else 0
        }

    def _handle_get_charging_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса зарядки всех дронов."""
        # ✅ Запрос списка дронов из DroneRegistry (через заглушку)
        # response = self.bus.request(
        #     self.registry_topics.LIST_DRONES,
        #     {"action": "list_drones", "payload": {}},
        #     timeout=5.0
        # )
        # drones = response.get("drones", []) if response else []
        
        # Временная заглушка
        drones = list(self._local_cache.values())
        charging_drones = [d for d in drones if d.get("status") == "charging"]
        
        return {
            "status": "ok",
            "payload": [
                {
                    "drone_id": d["drone_id"],
                    "battery_level": d.get("battery_level", 0),
                    "charging_power_w": d.get("charging_power_w", 0),
                    "target_battery": d.get("target_battery", 100)
                }
                for d in charging_drones
            ]
        }