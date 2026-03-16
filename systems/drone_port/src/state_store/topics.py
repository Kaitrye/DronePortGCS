"""
Топики для StateStore.
StateStore — пассивный компонент, не взаимодействует через SystemBus.
"""
from enum import Enum


class StateStoreTopics:
    """Топики хранилища состояния (только для аудита)."""
    
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    COMPONENT = "state_store"
    
    def __init__(self, system_id: str = "dp-001"):
        self.system_id = system_id
        self.base_topic = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.{self.COMPONENT}"
        
        # === Только для аудита (не используется в SystemBus) ===
        self.SAVE_PORT = f"{self.base_topic}.save_port"
        self.GET_PORT = f"{self.base_topic}.get_port"
        self.SAVE_DRONE = f"{self.base_topic}.save_drone"
        self.GET_DRONE = f"{self.base_topic}.get_drone"
        
        # === Actions (если понадобится аудит) ===
        self.ACTIONS = {
            "save_port": self.SAVE_PORT,
            "get_port": self.GET_PORT,
            "save_drone": self.SAVE_DRONE,
            "get_drone": self.GET_DRONE,
        }
    
    def get_topic_for_action(self, action: str) -> str:
        """Получить топик для действия."""
        return self.ACTIONS.get(action, f"{self.base_topic}.{action}")