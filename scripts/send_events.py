#!/usr/bin/env python3
"""Smoke event generator for security journal integration with Infopanel.

Connects to the same broker as the running Drone Port + GCS systems and
fires a handful of representative requests. Each request goes through the
normal handlers, which call ``_log_security`` — so the events end up in
the local NDJSON journal AND, if INFOPANEL_URL/INFOPANEL_API_KEY are
configured, get sent to Infopanel by the dispatcher.

Prerequisites:
    make docker-up
    make drone-port-system-up
    make gcs-system-up

Run via Makefile (handles env loading from docker/.env):
    make smoke-events
    make smoke-events SMOKE_ARGS="--system gcs --repeat 3"

Or directly (then you must export BROKER_TYPE/MQTT_BROKER/etc. yourself):
    python scripts/send_events.py
    python scripts/send_events.py --system drone_port
    python scripts/send_events.py --repeat 5

After the script finishes, wait ~5–10 seconds (InfopanelDispatcher flush
interval) and check the Infopanel UI: /log/safety with filter
``service=dronePort`` and ``service=GCS``.
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from typing import Any, Dict

# We talk to the broker directly, exactly like integration tests do.
from broker.src.bus_factory import create_system_bus

from systems.drone_port.src.drone_manager.topics import (
    ComponentTopics as DPDroneManagerTopics,
    DroneManagerActions as DPDroneManagerActions,
)
from systems.drone_port.src.orchestrator.topics import (
    ComponentTopics as DPOrchestratorTopics,
    OrchestratorActions as DPOrchestratorActions,
)
from systems.gcs.src.orchestrator.topics import (
    ComponentTopics as GCSOrchestratorTopics,
    OrchestratorActions as GCSOrchestratorActions,
)


SENDER = "smoke.send_events"


def _short(payload: Any) -> str:
    """Print only the first ~120 chars of a response so the log stays readable."""
    text = repr(payload)
    return text if len(text) <= 120 else text[:117] + "..."


def _request(bus, topic: str, action: str, data: Dict[str, Any], *, timeout: float = 5.0):
    msg = {"action": action, "sender": SENDER, "payload": data}
    return bus.request(topic, msg, timeout=timeout)


# -------- Drone Port scenarios --------

def scenario_dp_landing_random_drone(bus) -> None:
    drone_id = f"DR-SMOKE-{uuid.uuid4().hex[:6]}"
    resp = _request(
        bus,
        DPDroneManagerTopics.DRONE_MANAGER,
        DPDroneManagerActions.REQUEST_LANDING,
        {"drone_id": drone_id, "model": "TestX", "battery": 50},
    )
    print(f"  [dp] landing for {drone_id}  → {_short(resp)}")
    print("       expect in journal: info(request_landing.received) + "
          "notice(approved) | warning(no_free_ports)")


def scenario_dp_takeoff_unknown_drone(bus) -> None:
    """Triggers severity=error: registry lookup fails."""
    drone_id = f"DR-MISSING-{uuid.uuid4().hex[:6]}"
    resp = _request(
        bus,
        DPDroneManagerTopics.DRONE_MANAGER,
        DPDroneManagerActions.REQUEST_TAKEOFF,
        {"drone_id": drone_id},
    )
    print(f"  [dp] takeoff for unknown {drone_id}  → {_short(resp)}")
    print("       expect in journal: info(request_takeoff.received) + "
          "error(request_takeoff.registry_failed)")


def scenario_dp_get_available_drones(bus) -> None:
    resp = _request(
        bus,
        DPOrchestratorTopics.ORCHESTRATOR,
        DPOrchestratorActions.GET_AVAILABLE_DRONES,
        {},
    )
    print(f"  [dp] get_available_drones  → {_short(resp)}")
    print("       expect in journal: info(get_available_drones.received)")


# -------- GCS scenarios --------

def scenario_gcs_task_submit_valid(bus) -> None:
    resp = _request(
        bus,
        GCSOrchestratorTopics.GCS_ORCHESTRATOR,
        GCSOrchestratorActions.TASK_SUBMIT,
        {
            "type": "delivery",
            "waypoints": [
                {"lat": 55.0, "lon": 37.0, "alt": 50},
                {"lat": 55.1, "lon": 37.1, "alt": 50},
            ],
        },
        timeout=15.0,
    )
    print(f"  [gcs] task.submit (valid)  → {_short(resp)}")
    print("        expect in journal: info(task_submit.received) + "
          "notice(approved) | warning(failed)")


def scenario_gcs_task_submit_no_waypoints(bus) -> None:
    """Triggers severity=warning: planner can't build a route."""
    resp = _request(
        bus,
        GCSOrchestratorTopics.GCS_ORCHESTRATOR,
        GCSOrchestratorActions.TASK_SUBMIT,
        {"type": "delivery"},
        timeout=10.0,
    )
    print(f"  [gcs] task.submit (no waypoints)  → {_short(resp)}")
    print("        expect in journal: info(task_submit.received) + "
          "warning(task_submit.failed)")


def scenario_gcs_task_assign_unknown_mission(bus) -> None:
    """Triggers severity=error: mission converter fails."""
    resp = _request(
        bus,
        GCSOrchestratorTopics.GCS_ORCHESTRATOR,
        GCSOrchestratorActions.TASK_ASSIGN,
        {"mission_id": f"m-NONEXISTENT-{uuid.uuid4().hex[:6]}", "drone_id": "DR-1"},
        timeout=10.0,
    )
    print(f"  [gcs] task.assign (unknown mission)  → {_short(resp)}")
    print("        expect in journal: info(task_assign.received) + "
          "error(task_assign.mission_prepare_failed)")


# -------- Runner --------

DRONE_PORT_SCENARIOS = [
    scenario_dp_get_available_drones,
    scenario_dp_landing_random_drone,
    scenario_dp_takeoff_unknown_drone,
]

GCS_SCENARIOS = [
    scenario_gcs_task_submit_valid,
    scenario_gcs_task_submit_no_waypoints,
    scenario_gcs_task_assign_unknown_mission,
]


def run(system: str, repeat: int) -> None:
    client_id = f"smoke_send_events_{uuid.uuid4().hex[:8]}"
    print(f"Connecting to broker as {client_id} ...")
    bus = create_system_bus(client_id=client_id)
    bus.start()
    time.sleep(2)  # give MQTT/Kafka client time to actually connect

    try:
        for i in range(repeat):
            if repeat > 1:
                print(f"\n--- iteration {i + 1}/{repeat} ---")

            if system in ("drone_port", "both"):
                print("== Drone Port ==")
                for scenario in DRONE_PORT_SCENARIOS:
                    scenario(bus)
                    time.sleep(0.3)

            if system in ("gcs", "both"):
                print("== GCS / NUS ==")
                for scenario in GCS_SCENARIOS:
                    scenario(bus)
                    time.sleep(0.3)

            if i < repeat - 1:
                time.sleep(1)

        print("\nDone. Wait ~5–10s (InfopanelDispatcher flush_interval) and check:")
        print("  - Infopanel UI  → /log/safety  (filter service=dronePort / GCS)")
        print("  - Local NDJSON  → docker exec <security_monitor> "
              "cat /var/log/drones/security_journal.ndjson | tail")
    finally:
        bus.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--system",
        choices=["drone_port", "gcs", "both"],
        default="both",
        help="Which system(s) to fire requests against (default: both).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many times to run the full scenario list (default: 1).",
    )
    args = parser.parse_args()

    if args.repeat < 1:
        print("--repeat must be >= 1", file=sys.stderr)
        sys.exit(2)

    run(args.system, args.repeat)


if __name__ == "__main__":
    main()
