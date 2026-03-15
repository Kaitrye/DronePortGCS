"""Точка входа для запуска через python -m src.droneport_orchestrator"""
import os
from src.droneport_orchestrator.src.orchestrator import DroneportOrchestrator
from broker.system_bus import SystemBus

def main():
    system_id = os.getenv("SYSTEM_ID", "dp-001")
    bus = SystemBus(client_id=system_id)
    
    orchestrator = DroneportOrchestrator(
        system_id=system_id,
        name="DroneportOrchestrator",
        bus=bus
    )
    orchestrator.start()

if __name__ == "__main__":
    main()