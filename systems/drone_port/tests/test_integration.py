"""
E2E тесты dummy_system через реальный брокер.
Требует: make docker-up (kafka/mosquitto + dummy_component_a/b).
Если контейнеры не запущены — тесты пропускаются (skip).
"""
import pytest
import os
import time
import socket

from systems.drone_port.src.dp_comp_a.topics import (
    ComponentTopics,
    DummyComponentActions,
)


def _broker_available(retries=5, delay=2):
    bt = os.environ.get("BROKER_TYPE", "kafka").lower().strip().split("#")[0].strip()
    host = os.environ.get("BROKER_HOST", "localhost")
    port_val = (
        os.environ.get("MQTT_PORT", "1883")
        if bt == "mqtt"
        else os.environ.get("KAFKA_PORT", "9092")
    )
    port = int(port_val)
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(delay)
    return False


@pytest.fixture(scope="module")
def system_bus():
    if not _broker_available():
        pytest.skip(
            f"Broker ({os.environ.get('BROKER_TYPE', 'kafka')}) "
            f"at {os.environ.get('BROKER_HOST', 'localhost')} not available."
        )
    from broker.bus_factory import create_system_bus

    bt = os.environ.get("BROKER_TYPE", "kafka").lower().strip().split("#")[0].strip()
    host = os.environ.get("BROKER_HOST", "localhost")
    kafka_port = os.environ.get("KAFKA_PORT", "9092")
    mqtt_port = os.environ.get("MQTT_PORT", "1883")

    if not os.environ.get("BROKER_USER") and os.environ.get("ADMIN_USER"):
        os.environ["BROKER_USER"] = os.environ["ADMIN_USER"]
    if not os.environ.get("BROKER_PASSWORD") and os.environ.get("ADMIN_PASSWORD"):
        os.environ["BROKER_PASSWORD"] = os.environ["ADMIN_PASSWORD"]
    if bt == "kafka":
        os.environ["BROKER_TYPE"] = "kafka"
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", f"{host}:{kafka_port}"
        )
    else:
        os.environ["BROKER_TYPE"] = "mqtt"
        os.environ["MQTT_BROKER"] = os.environ.get("MQTT_BROKER", host)
        os.environ["MQTT_PORT"] = str(mqtt_port)

    bus = create_system_bus(client_id="test_client")
    bus.start()
    time.sleep(2)

    yield bus

    bus.stop()


