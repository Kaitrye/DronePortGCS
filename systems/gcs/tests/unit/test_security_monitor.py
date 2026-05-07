from sdk.security_journal import JournalRecorder
from systems.gcs import external_topics
from systems.gcs.src.orchestrator.topics import ComponentTopics as OrchestratorTopics
from systems.gcs.src.orchestrator.topics import OrchestratorActions
from systems.gcs.src.security_monitor.src.security_monitor import SecurityMonitorComponent
from systems.gcs.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions
from systems.gcs.topics import DroneActions


def _make_component(bus, tmp_path, *, policies=None):
    journal = JournalRecorder(
        file_path=str(tmp_path / "journal.ndjson"),
        service="GCS",
        service_id=1,
    )
    return SecurityMonitorComponent(
        component_id="gcs-monitor",
        bus=bus,
        policies=policies if policies is not None else set(),
        journal=journal,
    ), tmp_path / "journal.ndjson"


def _read_journal(path):
    import json
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_registers_security_monitor_handlers(mock_bus):
    component = SecurityMonitorComponent(component_id="gcs-monitor", bus=mock_bus)

    assert SecurityMonitorActions.PROXY_REQUEST in component._handlers
    assert SecurityMonitorActions.PROXY_PUBLISH in component._handlers
    assert SecurityMonitorActions.LIST_POLICIES in component._handlers
    assert SecurityMonitorActions.LOG_EVENT in component._handlers


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


# ---------- Security journal ----------

def test_handle_log_event_writes_to_journal(mock_bus, tmp_path):
    component, journal_path = _make_component(mock_bus, tmp_path)

    component._handle_log_event(
        {
            "action": SecurityMonitorActions.LOG_EVENT,
            "sender": "components.drone_manager",
            "payload": {
                "severity": "warning",
                "source_component": "drone_manager",
                "source_action": "task_submit.invalid",
                "message": "Invalid task",
                "details": {"task_id": "T-1"},
            },
        }
    )

    entry = _read_journal(journal_path)[-1]
    assert entry["severity"] == "warning"
    assert entry["service"] == "GCS"
    assert entry["service_id"] == 1
    assert entry["source_component"] == "drone_manager"
    assert entry["source_action"] == "task_submit.invalid"


def test_handle_log_event_ignores_self_publish(mock_bus, tmp_path):
    component, journal_path = _make_component(mock_bus, tmp_path)

    component._handle_log_event(
        {
            "action": SecurityMonitorActions.LOG_EVENT,
            "sender": component.topic,
            "payload": {
                "severity": "info",
                "source_component": "x",
                "source_action": "x",
                "message": "should be skipped",
            },
        }
    )

    assert not journal_path.exists() or _read_journal(journal_path) == []


def test_proxy_request_denied_writes_critical_to_journal(mock_bus, tmp_path):
    component, journal_path = _make_component(mock_bus, tmp_path, policies=set())

    component._handle_proxy_request(
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

    entry = _read_journal(journal_path)[-1]
    assert entry["severity"] == "critical"
    assert entry["source_action"] == "gcs.monitor.proxy_request.denied"
    assert entry["service"] == "GCS"


def test_severity_for_audit_classifier(mock_bus, tmp_path):
    component, _ = _make_component(mock_bus, tmp_path)

    assert component._severity_for_audit("x.denied") == "critical"
    assert component._severity_for_audit("x.invalid") == "alert"
    assert component._severity_for_audit("x.no_response") == "error"
    assert component._severity_for_audit("x.ok") == "info"
