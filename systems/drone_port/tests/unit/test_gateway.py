from systems.drone_port.src.gateway.src.gateway import DronePortGateway
from systems.drone_port.src.gateway.topics import ComponentTopics, GatewayActions, SystemTopics

def test_gateway_registers_all_routes(mock_bus):
    gateway = DronePortGateway(system_id="drone_port", bus=mock_bus)
    assert GatewayActions.GET_AVAILABLE_DRONES in gateway._handlers
    assert GatewayActions.REQUEST_LANDING in gateway._handlers
    assert GatewayActions.REQUEST_TAKEOFF in gateway._handlers
    assert gateway.topic == SystemTopics.DRONE_PORT

def test_gateway_proxies_get_available_drones_to_drone_registry(mock_bus):
    mock_bus.request.return_value = {
        "drones": [{"drone_id": "DR-1", "battery": 85.0}]
    }
    gateway = DronePortGateway(system_id="drone_port", bus=mock_bus)
    
    # Fixed: call the specific handler method instead of _handle_proxy
    result = gateway._handle_get_available_drones(
        {
            "action": GatewayActions.GET_AVAILABLE_DRONES,
            "payload": {},
        }
    )

    assert result == {"drones": [{"drone_id": "DR-1", "battery": 85.0}]}
    # Fixed: sender should match gateway.topic (SystemTopics.DRONE_PORT)
    mock_bus.request.assert_called_once_with(
        ComponentTopics.DRONE_REGISTRY,
        {
            "action": GatewayActions.GET_AVAILABLE_DRONES,
            "sender": SystemTopics.DRONE_PORT,
            "payload": {},
        },
        timeout=10.0,
    )

def test_gateway_proxies_landing_to_landing_manager(mock_bus):
    mock_bus.request.return_value = {"approved": True, "port_id": "P-01", "drone_id": "DR-1"}
    gateway = DronePortGateway(system_id="drone_port", bus=mock_bus)
    
    result = gateway._handle_request_landing(
        {
            "action": GatewayActions.REQUEST_LANDING,
            "payload": {"drone_id": "DR-1", "battery": 45.0},
        }
    )

    assert result == {"approved": True, "port_id": "P-01", "drone_id": "DR-1"}
    mock_bus.request.assert_called_once_with(
        ComponentTopics.LANDING_MANAGER,
        {
            "action": GatewayActions.REQUEST_LANDING,
            "sender": SystemTopics.DRONE_PORT,
            "payload": {"drone_id": "DR-1", "battery": 45.0},
        },
        timeout=10.0,
    )

def test_gateway_proxies_takeoff_to_takeoff_manager(mock_bus):
    mock_bus.request.return_value = {"approved": True, "drone_id": "DR-1", "battery": 85.0}
    gateway = DronePortGateway(system_id="drone_port", bus=mock_bus)
    
    result = gateway._handle_request_takeoff(
        {
            "action": GatewayActions.REQUEST_TAKEOFF,
            "payload": {"drone_id": "DR-1"},
        }
    )

    assert result == {"approved": True, "drone_id": "DR-1", "battery": 85.0}
    mock_bus.request.assert_called_once_with(
        ComponentTopics.TAKEOFF_MANAGER,
        {
            "action": GatewayActions.REQUEST_TAKEOFF,
            "sender": SystemTopics.DRONE_PORT,
            "payload": {"drone_id": "DR-1"},
        },
        timeout=10.0,
    )