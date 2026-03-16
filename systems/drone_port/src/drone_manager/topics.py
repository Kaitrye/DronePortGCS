"""
Топики для DroneManager.
Взаимодействие с физическими дронами и координация с другими компонентами.
"""
class DroneManagerTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.drone_manager"
        
        # === Команды от дронов ===
        self.REQUEST_LANDING = f"{self.base_topic}.request_landing"
        self.REQUEST_TAKEOFF = f"{self.base_topic}.request_takeoff"
        self.SELF_DIAGNOSTICS = f"{self.base_topic}.self_diagnostics"
        
        # === Исходящие события дронам ===
        self.LANDING_ALLOWED = f"{self.base_topic}.events.landing_allowed"
        self.TAKEOFF_ALLOWED = f"{self.base_topic}.events.takeoff_allowed"
        
        # === Запросы данных (общий для SITL и Эксплуатанта) ===
        self.GET_AVAILABLE_DRONES = f"{self.base_topic}.get_available_drones"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "request_landing": self.REQUEST_LANDING,
            "request_takeoff": self.REQUEST_TAKEOFF,
            "self_diagnostics": self.SELF_DIAGNOSTICS,
            "get_available_drones": self.GET_AVAILABLE_DRONES,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")