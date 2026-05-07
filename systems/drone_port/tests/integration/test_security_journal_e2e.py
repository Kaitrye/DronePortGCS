"""End-to-end smoke for security journal: in-memory bus + drone_manager + security_monitor."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdk.security_journal import JournalRecorder
from systems.drone_port.src.drone_manager.src.drone_manager import DroneManager
from systems.drone_port.src.drone_manager.topics import (
    ComponentTopics as DroneManagerTopics,
    DroneManagerActions,
)
from systems.drone_port.src.security_monitor.src.security_monitor import SecurityMonitorComponent
from systems.drone_port.src.security_monitor.topics import ExternalTopics, SecurityMonitorActions


def _read_journal(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _bind_components(integration_bus, journal_path, monkeypatch, *, policies=None):
    monkeypatch.setenv("SECURITY_MONITOR_TOPIC", ExternalTopics.DRONE_PORT)
    journal = JournalRecorder(
        file_path=str(journal_path),
        service="dronePort",
        service_id=1,
    )
    monitor = SecurityMonitorComponent(
        component_id="drone-port-monitor",
        bus=integration_bus,
        topic=ExternalTopics.DRONE_PORT,
        policies=policies if policies is not None else set(),
        journal=journal,
    )
    drone_manager = DroneManager(
        component_id="drone_manager",
        name="DroneManager",
        bus=integration_bus,
    )
    integration_bus.register(monitor)
    integration_bus.register(drone_manager)
    return monitor, drone_manager


def test_landing_no_free_ports_writes_to_journal(integration_bus, tmp_path, monkeypatch):
    journal_path = tmp_path / "security_journal.ndjson"
    _bind_components(integration_bus, journal_path, monkeypatch)

    integration_bus.request(
        DroneManagerTopics.DRONE_MANAGER,
        {
            "action": DroneManagerActions.REQUEST_LANDING,
            "sender": ExternalTopics.AGRODRON,
            "payload": {"drone_id": "DR-1", "model": "X9"},
        },
    )

    entries = _read_journal(journal_path)
    no_free = [e for e in entries if e["source_action"] == "request_landing.no_free_ports"]
    assert no_free, f"expected at least one no_free_ports entry; got: {entries}"
    entry = no_free[-1]
    assert entry["severity"] == "warning"
    assert entry["service"] == "dronePort"
    assert entry["source_component"] == "drone_port"
    assert entry["details"]["drone_id"] == "DR-1"


def test_proxy_request_denied_writes_critical(integration_bus, tmp_path, monkeypatch):
    journal_path = tmp_path / "security_journal.ndjson"
    _bind_components(integration_bus, journal_path, monkeypatch, policies=set())

    integration_bus.publish(
        ExternalTopics.DRONE_PORT,
        {
            "action": SecurityMonitorActions.PROXY_REQUEST,
            "sender": ExternalTopics.OPERATOR,
            "payload": {
                "target": {
                    "topic": ExternalTopics.DRONE_PORT,
                    "action": "get_available_drones",
                },
                "data": {},
            },
        },
    )

    entries = _read_journal(journal_path)
    denied = [e for e in entries if e["source_action"].endswith("proxy_request.denied")]
    assert denied, f"expected denied entry, got: {entries}"
    assert denied[-1]["severity"] == "critical"


def test_journal_record_has_infopanel_compatible_shape(integration_bus, tmp_path, monkeypatch):
    """The schema mirrors Infopanel POST /log/event — verify forward-compat fields."""
    journal_path = tmp_path / "security_journal.ndjson"
    _bind_components(integration_bus, journal_path, monkeypatch)

    integration_bus.request(
        DroneManagerTopics.DRONE_MANAGER,
        {
            "action": DroneManagerActions.REQUEST_LANDING,
            "sender": ExternalTopics.AGRODRON,
            "payload": {"drone_id": "DR-7"},
        },
    )

    entries = _read_journal(journal_path)
    assert entries
    entry = entries[-1]
    for required in ("timestamp_ms", "service", "service_id", "event_type", "severity", "message"):
        assert required in entry, f"missing required infopanel field: {required}"
    assert entry["event_type"] == "safety_event"
    assert entry["service"] in ("dronePort", "GCS")
    assert isinstance(entry["timestamp_ms"], int)
    assert isinstance(entry["service_id"], int)
    assert 1 <= entry["service_id"] <= 1000
    assert len(entry["message"]) <= 1024
