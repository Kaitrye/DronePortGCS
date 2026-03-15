"""
Топики для DroneRegistry.
Facade для сбора данных со всех компонентов.
"""

class DroneRegistryTopics:
    VERSION = "v1"
    SYSTEM_TYPE = "droneport"
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.BASE = f"{self.VERSION}.{self.SYSTEM_TYPE}.{self.system_id}.registry"
        
        # === Команды ===
        self.GET_AGGREGATED_FLEET_STATUS = f"{self.BASE}.get_aggregated_status"
        self.REGISTER_DRONE = f"{self.BASE}.register_drone"
        self.DELETE_DRONE = f"{self.BASE}.delete_drone"
        self.GET_DRONE = f"{self.BASE}.get_drone"
        self.LIST_DRONES = f"{self.BASE}.list_drones"
        self.UPDATE_DRONE_STATE = f"{self.BASE}.update_state"
        self.GET_CHARGING_DATA = f"{self.BASE}.get_charging_data"
        
        # === События ===
        self.EVENTS_BASE = f"{self.BASE}.events"
        self.DRONE_REGISTERED = f"{self.EVENTS_BASE}.registered"
        self.DRONE_DELETED = f"{self.EVENTS_BASE}.deleted"
        self.SAFETY_ALERT = f"{self.EVENTS_BASE}.safety_alert"