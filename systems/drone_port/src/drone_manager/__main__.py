"""Точка входа для запуска через python -m src.drone_manager"""
import os
from src.drone_manager.src.drone_manager import DroneManager
from broker.system_bus import SystemBus

def main():
    system_id = os.getenv("SYSTEM_ID", "dp-001")
    bus = SystemBus(client_id=system_id)
    
    manager = DroneManager(
        system_id=system_id,
        name="DroneManager",
        bus=bus
    )
    manager.start()

if __name__ == "__main__":
    main()