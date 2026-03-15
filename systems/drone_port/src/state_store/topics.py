"""
Топики для StateStore.
StateStore — пассивный компонент, не взаимодействует через SystemBus.
"""

class StateStoreTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.state_store"
        
        # Только для аудита
        self.SAVE_PORT = f"{self.BASE}.save_port"
        self.GET_PORT = f"{self.BASE}.get_port"