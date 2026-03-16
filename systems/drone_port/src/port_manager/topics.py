"""
Топики для PortManager.
"""
from enum import Enum


class PortManagerTopics:
    """Топики компонента управления посадочными площадками."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "port_manager"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Команды (входящие) ===
        self.RESERVE_SLOT = f"{self.base_topic}.reserve_slot"
        self.RELEASE_SLOT = f"{self.base_topic}.release_slot"
        self.REQUEST_LANDING_SLOT = f"{self.base_topic}.request_landing_slot"
        self.GET_PORT_STATUS = f"{self.base_topic}.get_port_status"
        
        # === События (исходящие) ===
        self.SLOT_RESERVED = f"{self.base_topic}.events.slot_reserved"
        self.SLOT_RELEASED = f"{self.base_topic}.events.slot_released"
        self.SLOT_ASSIGNED = f"{self.base_topic}.events.slot_assigned"
        
        # === Actions для BaseComponent ===
        self.ACTIONS = {
            "reserve_slot": self.RESERVE_SLOT,
            "release_slot": self.RELEASE_SLOT,
            "request_landing_slot": self.REQUEST_LANDING_SLOT,
            "get_port_status": self.GET_PORT_STATUS,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")