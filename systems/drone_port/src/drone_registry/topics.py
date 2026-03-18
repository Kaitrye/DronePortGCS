"""
Топики для DroneRegistry.
"""
class DroneRegistryTopics:
    """Топики компонента реестра дронов."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "registry"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) ===
        self.REGISTER_DRONE = f"{self.base_topic}.register_drone"
        self.LIST_DRONES = f"{self.base_topic}.list_drones"
        self.GET_AGGREGATED_STATUS = f"{self.base_topic}.get_aggregated_status"
        self.START_CHARGING = f"{self.base_topic}.start_charging"
        
        # === События (исходящие) ===
        self.DRONE_REGISTERED = f"{self.base_topic}.events.registered"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "register_drone": self.REGISTER_DRONE,
            "list_drones": self.LIST_DRONES,
            "get_aggregated_status": self.GET_AGGREGATED_STATUS,
            "start_charging": self.START_CHARGING,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")