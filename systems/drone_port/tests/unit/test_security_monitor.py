from systems.drone_port.src.drone_manager.topics import ComponentTopics as DroneManagerTopics
from systems.drone_port.src.drone_manager.topics import DroneManagerActions
from systems.drone_port.src.orchestrator.topics import ComponentTopics as OrchestratorTopics
from systems.drone_port.src.orchestrator.topics import OrchestratorActions
from systems.drone_port.src.security_monitor.src.security_monitor import SecurityMonitorComponent
from systems.drone_port.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions


def test_registers_security_monitor_handlers(mock_bus):
    component = SecurityMonitorComponent(component_id="drone-port-monitor", bus=mock_bus)

    assert SecurityMonitorActions.PROXY_REQUEST in component._handlers
    assert SecurityMonitorActions.PROXY_PUBLISH in component._handlers
    assert SecurityMonitorActions.LIST_POLICIES in component._handlers


def test_proxy_request_routes_operator_call_to_orchestrator(mock_bus):
    policies = {(ExternalTopics.OPERATOR, ExternalTopics.DRONE_PORT, OrchestratorActions.GET_AVAILABLE_DRONES)}
    component = SecurityMonitorComponent(component_id="drone-port-monitor", bus=mock_bus, policies=policies)
    mock_bus.request.return_value = {"success": True, "payload": {"drones": []}}

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.OPERATOR,
            "payload": {
                "target": {
                    "topic": ExternalTopics.DRONE_PORT,
                    "action": OrchestratorActions.GET_AVAILABLE_DRONES,
                },
                "data": {},
            },
        }
    )

    assert response == {
        "target_topic": ExternalTopics.DRONE_PORT,
        "target_action": OrchestratorActions.GET_AVAILABLE_DRONES,
        "target_response": {"success": True, "payload": {"drones": []}},
    }
    mock_bus.request.assert_called_once_with(
        OrchestratorTopics.ORCHESTRATOR,
        {
            "action": OrchestratorActions.GET_AVAILABLE_DRONES,
            "sender": component.topic,
            "payload": {},
        },
        timeout=10.0,
    )


def test_proxy_request_routes_agrodron_call_to_drone_manager(mock_bus):
    policies = {(ExternalTopics.AGRODRON, ExternalTopics.DRONE_PORT, DroneManagerActions.REQUEST_LANDING)}
    component = SecurityMonitorComponent(component_id="drone-port-monitor", bus=mock_bus, policies=policies)
    mock_bus.request.return_value = {"approved": True, "port_id": "P-1"}

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.AGRODRON,
            "payload": {
                "target": {
                    "topic": ExternalTopics.DRONE_PORT,
                    "action": DroneManagerActions.REQUEST_LANDING,
                },
                "data": {"drone_id": "DR-1"},
            },
        }
    )

    assert response == {
        "target_topic": ExternalTopics.DRONE_PORT,
        "target_action": DroneManagerActions.REQUEST_LANDING,
        "target_response": {"approved": True, "port_id": "P-1"},
    }
    mock_bus.request.assert_called_once_with(
        DroneManagerTopics.DRONE_MANAGER,
        {
            "action": DroneManagerActions.REQUEST_LANDING,
            "sender": component.topic,
            "payload": {"drone_id": "DR-1"},
        },
        timeout=10.0,
    )


def test_proxy_publish_routes_to_raw_sitl_topic(mock_bus):
    policies = {(ExternalTopics.DRONE_PORT, ExternalTopics.SITL, SecurityMonitorActions.SITL_HOME_PUBLISH)}
    component = SecurityMonitorComponent(component_id="drone-port-monitor", bus=mock_bus, policies=policies)
    mock_bus.publish.return_value = True

    response = component._handle_proxy_publish(
        {
            "sender": ExternalTopics.DRONE_PORT,
            "payload": {
                "target": {
                    "topic": ExternalTopics.SITL,
                    "action": SecurityMonitorActions.SITL_HOME_PUBLISH,
                },
                "data": {"drone_id": "DR-1", "home_lat": 1.0, "home_lon": 2.0, "home_alt": 3.0},
            },
        }
    )

    assert response == {"published": True}
    mock_bus.publish.assert_called_once_with(
        ExternalTopics.SITL,
        {"drone_id": "DR-1", "home_lat": 1.0, "home_lon": 2.0, "home_alt": 3.0},
    )


def test_proxy_request_denies_when_policy_absent(mock_bus):
    component = SecurityMonitorComponent(component_id="drone-port-monitor", bus=mock_bus, policies=set())

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.OPERATOR,
            "payload": {
                "target": {
                    "topic": ExternalTopics.DRONE_PORT,
                    "action": OrchestratorActions.GET_AVAILABLE_DRONES,
                },
                "data": {},
            },
        }
    )

    assert response is None
    mock_bus.request.assert_not_called()
