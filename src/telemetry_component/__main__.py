import os

from broker.bus_factory import create_system_bus
from systems.gcs.src.telemetry_component.src.telemetry_component import TelemetryComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "gcs_telemetry")
    health_port = int(os.environ.get("HEALTH_PORT", "9804"))

    bus = create_system_bus(client_id=component_id)
    component = TelemetryComponent(system_id=component_id, bus=bus, health_port=health_port)
    component.run_forever()


if __name__ == "__main__":
    main()
