import pytest

from systems.drone_port.src.port_manager.src.port_manager import PortManager
from systems.drone_port.src.port_manager.topics import PortManagerActions


@pytest.fixture
def component(mock_bus):
    return PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)


def test_registers_port_manager_handlers(component):
    assert PortManagerActions.OCCUPY_PORT in component._handlers
    assert PortManagerActions.RELEASE_PORT in component._handlers


def test_occupy_port_reserves_first_free_port(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)

    result = manager._handle_occupy_port({"payload": {"drone_id": "DR-1"}})

    assert result == {"port_id": "P-01"}
    assert manager._ports["P-01"]["drone_id"] == "DR-1"
    assert manager._ports["P-01"]["status"] == "occupied"


def test_occupy_port_skips_occupied_ports(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)
    manager._ports["P-01"]["drone_id"] = "DR-X"
    manager._ports["P-01"]["status"] = "occupied"

    result = manager._handle_occupy_port({"payload": {"drone_id": "DR-2"}})

    assert result == {"port_id": "P-02"}
    assert manager._ports["P-02"]["drone_id"] == "DR-2"


def test_occupy_port_returns_error_when_no_free_ports(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)
    for port in manager._ports.values():
        port["drone_id"] = "DR-X"
        port["status"] = "occupied"

    result = manager._handle_occupy_port({"payload": {"drone_id": "DR-3"}})

    assert result == {"error": "No free ports"}


def test_occupy_port_returns_error_without_drone_id(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)

    result = manager._handle_occupy_port({"payload": {}})

    assert result == {"error": "drone_id required"}


def test_release_port_frees_occupied_port(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)
    manager._ports["P-01"]["drone_id"] = "DR-1"
    manager._ports["P-01"]["status"] = "occupied"

    manager._handle_release_port({"payload": {"port_id": "P-01", "drone_id": "DR-1"}})

    assert manager._ports["P-01"]["drone_id"] is None
    assert manager._ports["P-01"]["status"] == "free"


def test_release_port_does_nothing_for_invalid_port(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)

    manager._handle_release_port({"payload": {"port_id": "INVALID", "drone_id": "DR-1"}})

    # Ничего не изменилось
    for port in manager._ports.values():
        assert port["drone_id"] is None
        assert port["status"] == "free"


def test_release_port_handles_missing_port_id(mock_bus):
    manager = PortManager(component_id="port_manager", name="PortManager", bus=mock_bus)

    result = manager._handle_release_port({"payload": {"drone_id": "DR-1"}})
    assert result is None