"""
DroneportSystem — главная система, оркестрирующая компоненты.
Соответствует контракту из DronePort.md и C4-схеме.
"""

import datetime
from typing import Dict, Any, Optional
from shared.base_system import BaseSystem
from shared.topics import SystemTopics, DroneportActions
from broker.system_bus import SystemBus
from state_store.src.state_store import StateStore
from port_manager.src.port_manager import PortManager
from power_health_manager.src.power_health_manager import PowerHealthManager
from drone_registry.src.drone_registry import DroneRegistry


class DroneportSystem(BaseSystem):
    def __init__(
        self,
        system_id: str,
        name: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        super().__init__(
            system_id=system_id,
            system_type="droneport",
            topic=SystemTopics.DRONEPORT,
            bus=bus,
            health_port=health_port,
        )
        self.name = name
        print(f"DroneportSystem '{name}' initialized")

        # DI: внедрение компонентов
        self.state = StateStore()
        self.port_manager = PortManager(self.state)
        self.power_health = PowerHealthManager(self.state)
        self.drone_registry = DroneRegistry(self.state)._register_handlers()

    def _register_handlers(self) -> None:
        self.register_handler(DroneportActions.RESERVE_SLOTS, self._handle_reserve_slots)
        self.register_handler(DroneportActions.PREFLIGHT_CHECK, self._handle_preflight_check)
        self.register_handler(DroneportActions.CHARGE_TO_THRESHOLD, self._handle_charge_to_threshold)
        self.register_handler(DroneportActions.RELEASE_FOR_TAKEOFF, self._handle_release_for_takeoff)
        self.register_handler(DroneportActions.REQUEST_LANDING_SLOT, self._handle_request_landing_slot)
        self.register_handler(DroneportActions.DOCK, self._handle_dock)
        self.register_handler(DroneportActions.EMERGENCY_RECEIVE, self._handle_emergency_receive)
        self.register_handler(DroneportActions.HEALTH_CHECK, self._handle_health_check)
        self.register_handler(DroneportActions.OPERATOT_REPORT_REQUEST, self._handle_operator_report_request)

    def _handle_reserve_slots(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_ids = payload.get("drone_ids", [])
        mission_window = payload.get("mission_window", {})

        results = []
        for did in drone_ids:
            res = self.port_manager.reserve_slot(
                drone_id=did,
                port_id=f"P-{len(results)+1}",  # упрощённо — можно заменить на алгоритм выбора
                mission_window=mission_window
            )
            results.append(res)

        return {
            "status": "reserved" if all(r.get("status") == "reserved" for r in results) else "partial",
            "results": results
        }

    def _handle_preflight(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        if not drone_id:
            return {"status": "preflight.failed", "error_code": "INVALID_PAYLOAD", "reason": "drone_id_required"}
        return {"status": "preflight.ok", "drone_id": drone_id}

    def _handle_charge_to_threshold(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        min_battery = float(payload.get("min_battery", 90.0))
        current_battery = float(payload.get("current_battery", 50.0))
        dep_time = payload.get("departure_time_sec", 3600)

        return self.power_health.charge_to_threshold(
            drone_id=drone_id,
            min_battery=min_battery,
            current_battery=current_battery,
            departure_time_sec=dep_time
        )

    def _handle_release_for_takeoff(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        return self.port_manager.release_for_takeoff(drone_id)

    def _handle_request_landing_slot(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        return self.port_manager.request_landing_slot(drone_id)

    def _handle_dock(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        if not drone_id:
            return {"status": "docked.failed", "reason": "drone_id_required"}

        diag = self.power_health.run_post_landing_diagnostics(drone_id)
        if diag["status"] == "diagnostics.ok":
            self.power_health.auto_start_charging_if_needed(drone_id)

        return {"status": "docked", "drone_id": drone_id}

    def _handle_emergency_receive(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id")
        return {"status": "emergency_ack", "drone_id": drone_id}

    def _handle_health_check(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "health.ok", "timestamp": message.get("timestamp")}

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            "name": self.name,
            "drones_total": len(self.drone_registry.list_all_drones()),
            "ports_occupied": sum(
                1 for p in self.state.redis.keys("port:*")
                if self.state.is_port_occupied(p.split(":")[1])
            ),
        })
        return status

    def _handle_operator_report_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает запрос от НУС на получение сводной информации.
        Агрегирует данные и публикует ответ в системную шину.
        """
        # 1. Сбор данных через StateStore
        report_data = self.state.get_aggregated_fleet_status()
        
        # 2. Добавление мета-информации о самом дронопорте
        report_data["droneport_id"] = self.system_id
        report_data["droneport_name"] = self.name
        report_data["system_health"] = "healthy" # Можно заменить на реальную проверку
        
        # 3. Формирование ответа
        response = {
            "status": "report_generated",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": report_data
        }
        
        # 4. (Опционально) Отправка асинхронного события в топик отчетов
        # self.bus.publish(SystemTopics.OPERATOR_REPORTS, response)
        
        return response

    def get_status(self) -> Dict[str, Any]:
        """Обновленный метод статуса с корректной логикой."""
        status = super().get_status()
        
        # Безопасный подсчет занятых портов
        occupied_count = 0
        ports = self.state.get_all_ports_status()
        for p in ports:
            if p.get("drone_id"): # Если поле не пустое
                occupied_count += 1
                
        status.update({
            "name": self.name,
            "drones_total": len(self.drone_registry.list_all_drones()),
            "ports_occupied": occupied_count,
            "ports_total": len(ports)
        })
        return status