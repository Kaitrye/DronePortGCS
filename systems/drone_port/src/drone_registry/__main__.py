"""Точка входа для запуска через python -m src.drone_registry"""
import os
from src.drone_registry.src.drone_registry import DroneRegistry
from broker.system_bus import SystemBus
from src.state_store.src.state_store import StateStore

def main():
    system_id = os.getenv("SYSTEM_ID", "dp-001")
    bus = SystemBus(client_id=system_id)
    state_store = StateStore()
    
    registry = DroneRegistry(
        system_id=system_id,
        name="DroneRegistry",
        bus=bus,
        state_store=state_store
    )
    registry.start()

if __name__ == "__main__":
    main()