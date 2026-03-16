"""Точка входа для DroneportOrchestrator."""
import os
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, ROOT_DIR)

from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.droneport_orchestrator.src.orchestrator import DroneportOrchestrator


def main():
    component_id = os.getenv("COMPONENT_ID", "orchestrator")
    broker_host = os.getenv("BROKER_HOST", "mqtt")
    broker_port = int(os.getenv("BROKER_PORT", 1883))

    bus = MQTTSystemBus(
        broker=broker_host,
        port=broker_port,
        client_id=component_id
    )
    bus.start()

    orchestrator = DroneportOrchestrator(
        component_id=component_id,
        name=component_id,
        bus=bus,
    )
    
    orchestrator.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()


if __name__ == "__main__":
    main()