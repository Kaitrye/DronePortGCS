"""Точка входа для запуска через python -m src.port_manager"""
import os
from src.port_manager.src.port_manager import PortManager
from broker.system_bus import SystemBus
from src.state_store.src.state_store import StateStore

def main():
    system_id = os.getenv("SYSTEM_ID", "dp-001")
    bus = SystemBus(client_id=system_id)
    state_store = StateStore()
    
    manager = PortManager(
        system_id=system_id,
        name="PortManager",
        bus=bus,
        state_store=state_store
    )
    manager.start()

if __name__ == "__main__":
    main()