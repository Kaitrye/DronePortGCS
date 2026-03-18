"""Точка входа для DroneRegistry."""
import os
import signal
import time

from broker.bus_factory import create_system_bus
from systems.drone_port.src.drone_registry.src.drone_registry import DroneRegistry


def main() -> None:
    component_id = os.environ.get("COMPONENT_ID", "drone_registry")
    bus = create_system_bus(client_id=component_id)
    component = DroneRegistry(
        component_id=component_id,
        name=component_id,
        bus=bus
    )

    def _shutdown(sig, frame):
        print(f"\n[{component_id}] Received signal {sig}, shutting down...")
        component.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    component.start()
    print(f"[{component_id}] Running. Press Ctrl+C to stop.")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()