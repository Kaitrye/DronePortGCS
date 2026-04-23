from systems.gcs import external_topics
from systems.gcs.src.orchestrator.topics import ComponentTopics as OrchestratorTopics
from systems.gcs.src.orchestrator.topics import OrchestratorActions
from systems.gcs.src.security_monitor.src.security_monitor import SecurityMonitorComponent
from systems.gcs.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions
from systems.gcs.topics import DroneActions


def test_registers_security_monitor_handlers(mock_bus):
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus)

    assert SecurityMonitorActions.PROXY_REQUEST in component._handlers
    assert SecurityMonitorActions.PROXY_PUBLISH in component._handlers
    assert SecurityMonitorActions.LIST_POLICIES in component._handlers


def test_proxy_request_routes_operator_call_to_orchestrator(mock_bus):
    policies = {(ExternalTopics.OPERATOR, ExternalTopics.GCS, OrchestratorActions.TASK_SUBMIT)}
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus, policies=policies)
    mock_bus.request.return_value = {"success": True, "payload": {"ok": True}}

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.OPERATOR,
            "payload": {
                "target": {
                    "topic": ExternalTopics.GCS,
                    "action": OrchestratorActions.TASK_SUBMIT,
                },
                "data": {"task_id": "T-1"},
            },
        }
    )

    assert response == {
        "target_topic": ExternalTopics.GCS,
        "target_action": OrchestratorActions.TASK_SUBMIT,
        "target_response": {"success": True, "payload": {"ok": True}},
    }
    mock_bus.request.assert_called_once_with(
        OrchestratorTopics.GCS_ORCHESTRATOR,
        {
            "action": OrchestratorActions.TASK_SUBMIT,
            "sender": component.topic,
            "payload": {"task_id": "T-1"},
        },
        timeout=10.0,
    )


def test_proxy_request_denies_when_policy_absent(mock_bus):
    policies = set()
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus, policies=policies)

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.OPERATOR,
            "payload": {
                "target": {
                    "topic": ExternalTopics.GCS,
                    "action": OrchestratorActions.TASK_SUBMIT,
                },
                "data": {},
            },
        }
    )

    assert response is None
    mock_bus.request.assert_not_called()


def test_proxy_request_routes_to_agrodron_monitor_and_unwraps_response(mock_bus):
    policies = {(ExternalTopics.GCS, ExternalTopics.AGRODRON, DroneActions.TELEMETRY_GET)}
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus, policies=policies)
    mock_bus.request.return_value = {
        "payload": {
            "target_response": {
                "success": True,
                "payload": {"telemetry": {"battery": 88}},
            }
        }
    }

    response = component._handle_proxy_request(
        {
            "sender": ExternalTopics.GCS,
            "payload": {
                "target": {
                    "topic": ExternalTopics.AGRODRON,
                    "action": DroneActions.TELEMETRY_GET,
                },
                "data": {"drone_id": "dr-1"},
            },
        }
    )

    assert response == {
        "target_topic": ExternalTopics.AGRODRON,
        "target_action": DroneActions.TELEMETRY_GET,
        "target_response": {
            "success": True,
            "payload": {"telemetry": {"battery": 88}},
        },
    }
    mock_bus.request.assert_called_once_with(
        external_topics.ExternalTopics.AGRODRON_SECURITY_MONITOR,
        {
            "action": SecurityMonitorActions.PROXY_REQUEST,
            "sender": component.topic,
            "payload": {
                "target": {
                    "topic": external_topics.ExternalTopics.AGRODRON_TELEMETRY,
                    "action": DroneActions.TELEMETRY_GET,
                },
                "data": {"drone_id": "dr-1"},
            },
        },
        timeout=10.0,
    )


def test_proxy_publish_routes_to_agrodron_monitor(mock_bus):
    policies = {(ExternalTopics.GCS, ExternalTopics.AGRODRON, DroneActions.CMD)}
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus, policies=policies)
    mock_bus.publish.return_value = True

    response = component._handle_proxy_publish(
        {
            "sender": ExternalTopics.GCS,
            "payload": {
                "target": {
                    "topic": ExternalTopics.AGRODRON,
                    "action": DroneActions.CMD,
                },
                "data": {"command": "START"},
            },
        }
    )

    assert response == {"published": True}
    mock_bus.publish.assert_called_once_with(
        external_topics.ExternalTopics.AGRODRON_SECURITY_MONITOR,
        {
            "action": SecurityMonitorActions.PROXY_PUBLISH,
            "sender": component.topic,
            "payload": {
                "target": {
                    "topic": external_topics.ExternalTopics.AGRODRON_AUTOPILOT,
                    "action": DroneActions.CMD,
                },
                "data": {"command": "START"},
            },
        },
    )
