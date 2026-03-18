"""
Топики для DroneManager.
"""
class DroneManagerTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "drone_manager"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) ===
        self.REQUEST_LANDING = f"{self.base_topic}.request_landing"
        self.REQUEST_TAKEOFF = f"{self.base_topic}.request_takeoff"
        self.REQUEST_CHARGING = f"{self.base_topic}.request_charging"  # новый метод
        self.GET_AVAILABLE_DRONES = f"{self.base_topic}.get_available_drones"
        
        # === События (исходящие) ===
        self.LANDING_ALLOWED = f"{self.base_topic}.events.landing_allowed"
        self.TAKEOFF_ALLOWED = f"{self.base_topic}.events.takeoff_allowed"
        self.CHARGING_REQUESTED = f"{self.base_topic}.events.charging_requested"
        
        # === Actions ===
        self.ACTIONS = {
            "request_landing": self.REQUEST_LANDING,
            "request_takeoff": self.REQUEST_TAKEOFF,
            "request_charging": self.REQUEST_CHARGING,  # новый action
            "get_available_drones": self.GET_AVAILABLE_DRONES,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")