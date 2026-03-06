"""
PortManager — управление посадочными площадками.
Реализует команды: reserve_slots, request_landing_slot, release_for_takeoff.
"""

from typing import Dict, Any, List, Optional
from src.state_store.src.state_store import StateStore


class PortManager:
    def __init__(self, state_store: StateStore):
        self.state = state_store

    def reserve_slot(
        self,
        drone_id: str,
        port_id: str,
        mission_window: Dict[str, str]
    ) -> Dict[str, Any]:
        if self.state.is_port_occupied(port_id):
            return {
                "status": "rejected",
                "error_code": "PORT_RESOURCE_BUSY",
                "reason": f"Port {port_id} is occupied",
                "retryable": True
            }

        self.state.save_port(port_id, {
            "port_id": port_id,
            "drone_id": drone_id,
            "status": "reserved",
            "mission_window_start": mission_window.get("start"),
            "mission_window_end": mission_window.get("end")
        })

        self.state.save_drone(drone_id, {
            "drone_id": drone_id,
            "port_id": port_id,
            "status": "reserved",
            "battery_level": "0.0"
        })

        return {
            "status": "reserved",
            "port_id": port_id,
            "drone_id": drone_id
        }

    def request_landing_slot(
        self,
        drone_id: str,
        preferred_ports: List[str] = None
    ) -> Dict[str, Any]:
        ports = preferred_ports or ["P-01", "P-02", "P-03", "P-04"]
        for pid in ports:
            if not self.state.is_port_occupied(pid):
                return {
                    "status": "slot_assigned",
                    "port_id": pid,
                    "drone_id": drone_id
                }
        return {
            "status": "denied",
            "error_code": "PORT_RESOURCE_BUSY",
            "reason": "No available slots",
            "retryable": True
        }

    def release_for_takeoff(self, drone_id: str) -> Dict[str, Any]:
        drone = self.state.get_drone(drone_id)
        if not drone:
            return {"status": "failed", "reason": "Drone not found"}

        port_id = drone.get("port_id")
        if port_id:
            self.state.save_port(port_id, {
                "port_id": port_id,
                "drone_id": "",
                "status": "free"
            })
            self.state.delete_drone(drone_id)

        return {"status": "release_ack", "drone_id": drone_id}
    
    def _validate_drone_compatibility(self, drone_id: str, port_id: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Проверяет:
        1. Совместимость типа дрона с портом (габариты, протокол).
        2. Способность порта обеспечить физическую безопасность.
        3. Исправность оборудования порта.
        Возвращает: (is_ok, error_code, reason)
        """
        # 1. Проверка мета-данных дрона
        specs = self.state.get_drone_meta(drone_id)
        port_data = self.state.get_port(port_id)
        
        if specs and port_data:
            # Пример: проверка типа дрона
            if specs.get("drone_type") == "heavy_cargo" and port_data.get("max_load_kg", 0) < 50:
                return False, "DRONE_TYPE_MISMATCH", "Port cannot handle heavy cargo drones"
            
            # Пример: проверка протокола связи
            if specs.get("protocol") != port_data.get("supported_protocol"):
                return False, "PROTOCOL_MISMATCH", "Communication protocol incompatible"

        # 2. Проверка статуса оборудования порта
        if port_data and port_data.get("maintenance_mode") == "true":
            return False, "PORT_MAINTENANCE", "Port equipment under maintenance"
            
        # 3. Проверка политик безопасности (например, погодные ограничения)
        # Здесь можно добавить вызов внешнего сервиса погоды
        # if not self._is_weather_safe(port_id): return False, "WEATHER_UNSAFE", ...

        return True, None, None

    def request_landing_slot(self, drone_id: str, preferred_ports: List[str] = None, drone_telemetry: Dict = None) -> Dict[str, Any]:
        """
        Запрос на посадку с полной валидацией.
        drone_telemetry: данные, пришедшие напрямую от дрона (GPS, battery, sensors).
        """
        ports = preferred_ports or ["P-01", "P-02", "P-03", "P-04"]
        
        for pid in ports:
            # 1. Базовая проверка занятости
            if self.state.is_port_occupied(pid):
                continue
                
            # 2. НОВАЯ ЛОГИКА: Валидация безопасности и совместимости
            is_valid, err_code, reason = self._validate_drone_compatibility(drone_id, pid)
            if not is_valid:
                # Если порт не подошел по безопасности, идем дальше или возвращаем ошибку, 
                # если это единственный вариант.
                continue 

            # 3. Успешное резервирование
            return {
                "status": "slot_assigned",
                "port_id": pid,
                "drone_id": drone_id,
                "corridor": self._generate_landing_corridor(pid) # Вспомогательный метод
            }
            
        # Если цикл закончился без возврата
        return {
            "status": "denied",
            "error_code": "NO_SUITABLE_SLOTS",
            "reason": "No available slots meeting safety/compatibility requirements",
            "retryable": True
        }

    def _generate_landing_corridor(self, port_id: str) -> Dict[str, Any]:
        """Генерирует параметры коридора для посадки (упрощенно)."""
        return {
            "entry_point": f"{port_id}-ENTRY",
            "altitude_m": 50,
            "approach_vector": "NORTH"
        }