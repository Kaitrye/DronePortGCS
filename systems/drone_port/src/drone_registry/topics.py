"""
Топики для DroneRegistry.
"""
from enum import Enum


class DroneRegistryTopics:
    """Топики компонента реестра дронов (Facade)."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "registry"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) ===
        self.GET_AGGREGATED_FLEET_STATUS = f"{self.base_topic}.get_aggregated_status"
        self.REGISTER_DRONE = f"{self.base_topic}.register_drone"
        self.DELETE_DRONE = f"{self.base_topic}.delete_drone"
        self.GET_DRONE = f"{self.base_topic}.get_drone"
        self.LIST_DRONES = f"{self.base_topic}.list_drones"
        self.UPDATE_DRONE_STATE = f"{self.base_topic}.update_state"
        self.GET_CHARGING_DATA = f"{self.base_topic}.get_charging_data"
        
        # === События (исходящие) ===
        self.DRONE_REGISTERED = f"{self.base_topic}.events.registered"
        self.DRONE_DELETED = f"{self.base_topic}.events.deleted"
        self.SAFETY_ALERT = f"{self.base_topic}.events.safety_alert"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "get_aggregated_status": self.GET_AGGREGATED_FLEET_STATUS,
            "register_drone": self.REGISTER_DRONE,
            "delete_drone": self.DELETE_DRONE,
            "get_drone": self.GET_DRONE,
            "list_drones": self.LIST_DRONES,
            "update_state": self.UPDATE_DRONE_STATE,
            "get_charging_data": self.GET_CHARGING_DATA,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")