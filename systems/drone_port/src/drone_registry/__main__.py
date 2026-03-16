"""Точка входа для DroneRegistry."""
import os
import sys
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, ROOT_DIR)

from broker.mqtt.mqtt_system_bus import MQTTSystemBus
from systems.drone_port.src.state_store.src.state_store import StateStore
from systems.drone_port.src.drone_registry.src.drone_registry import DroneRegistry


def main():
    component_id = os.getenv("COMPONENT_ID", "drone_registry")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    broker_host = os.getenv("BROKER_HOST", "mqtt")
    broker_port = int(os.getenv("BROKER_PORT", 1883))

    # Инициализация StateStore
    state_store = StateStore(redis_host=redis_host, redis_port=redis_port)
    
    # Инициализация MQTT SystemBus
    bus = MQTTSystemBus(
        broker=broker_host,
        port=broker_port,
        client_id=component_id
    )
    bus.start()

    # ✅ Исправлено: component_id вместо system_id, без health_port
    registry = DroneRegistry(
        component_id=component_id,
        name=component_id,
        bus=bus,
        state_store=state_store,
    )
    
    # ✅ Запуск через start() вместо run()
    registry.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        registry.stop()


if __name__ == "__main__":
    main()