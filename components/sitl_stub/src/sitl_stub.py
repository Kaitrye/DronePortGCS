"""Temporary SITL telemetry stub.

Listens on the raw ``sitl.telemetry.request`` topic and returns a minimal
telemetry payload so navigation/security_monitor requests stop timing out.
"""

from __future__ import annotations

import os
import signal
import math
import sys
import threading
import time
from typing import Any, Dict

from broker.src.bus_factory import create_system_bus


def _build_initial_state() -> Dict[str, Any]:
    return {
        "lat": float(os.environ.get("SITL_STUB_LAT", "55.7522")),
        "lon": float(os.environ.get("SITL_STUB_LON", "37.6156")),
        "alt": float(os.environ.get("SITL_STUB_ALT", "12.0")),
        "relative_alt": float(os.environ.get("SITL_STUB_RELATIVE_ALT", "12.0")),
        "vx": float(os.environ.get("SITL_STUB_VX", "0.0")),
        "vy": float(os.environ.get("SITL_STUB_VY", "0.0")),
        "vz": float(os.environ.get("SITL_STUB_VZ", "0.0")),
        "yaw_deg": float(os.environ.get("SITL_STUB_YAW_DEG", "90.0")),
        "battery_pct": float(os.environ.get("SITL_STUB_BATTERY_PCT", "87.0")),
        "mode": os.environ.get("SITL_STUB_MODE", "HOLD"),
    }


def _build_response_payload(
    request_payload: Dict[str, Any], state: Dict[str, Any]
) -> Dict[str, Any]:
    drone_ids = request_payload.get("drone_id")
    drone_id = "drone_001"
    if isinstance(drone_ids, list) and drone_ids:
        drone_id = str(drone_ids[0])
    elif isinstance(drone_ids, str) and drone_ids:
        drone_id = drone_ids

    return {
        "drone_id": drone_id,
        "lat": float(state.get("lat", 0.0)),
        "lon": float(state.get("lon", 0.0)),
        "alt": float(state.get("alt", 0.0)),
        "relative_alt": float(state.get("relative_alt", state.get("alt", 0.0))),
        "vx": float(state.get("vx", 0.0)),
        "vy": float(state.get("vy", 0.0)),
        "vz": float(state.get("vz", 0.0)),
        "yaw_deg": float(state.get("yaw_deg", 0.0)),
        "gps_valid": True,
        "fix": "3D",
        "satellites": 10,
        "hdop": 0.8,
        "battery_pct": float(state.get("battery_pct", 0.0)),
        "mode": str(state.get("mode", "HOLD")),
        "timestamp": time.time(),
    }


def _meters_to_lat_lon_delta(vx: float, vy: float, lat_deg: float, dt_s: float) -> tuple[float, float]:
    meters_per_degree_lat = 111_111.0
    lat_rad = math.radians(lat_deg)
    meters_per_degree_lon = max(1.0, meters_per_degree_lat * math.cos(lat_rad))
    delta_lat = (vy * dt_s) / meters_per_degree_lat
    delta_lon = (vx * dt_s) / meters_per_degree_lon
    return delta_lat, delta_lon

def main() -> None:
    topic = os.environ.get("SITL_TELEMETRY_REQUEST_TOPIC", "sitl.telemetry.request").strip()
    sitl_topic = os.environ.get("SITL_TOPIC", "v1.SITL.SITL001.main").strip()
    sitl_commands_topic = os.environ.get("SITL_COMMANDS_TOPIC", sitl_topic).strip() or sitl_topic
    client_id = os.environ.get("COMPONENT_ID", "sitl_stub")
    running = True
    retry_delay_s = float(os.environ.get("SITL_STUB_RETRY_DELAY_S", "2.0"))
    tick_s = float(os.environ.get("SITL_STUB_TICK_S", "0.2"))
    command_hold_s = float(os.environ.get("SITL_STUB_COMMAND_HOLD_S", "2.0"))
    idle_drain_pct_per_s = float(os.environ.get("SITL_STUB_BATTERY_IDLE_DRAIN_PCT_PER_S", "0.001"))
    move_drain_pct_per_mps_s = float(os.environ.get("SITL_STUB_BATTERY_MOVE_DRAIN_PCT_PER_MPS_S", "0.006"))
    vertical_drain_pct_per_mps_s = float(os.environ.get("SITL_STUB_BATTERY_VERTICAL_DRAIN_PCT_PER_MPS_S", "0.01"))
    state = _build_initial_state()
    state["last_motion_update_ts"] = time.time()
    state["last_command_ts"] = 0.0
    state_lock = threading.Lock()

    def handle_request(message: Dict[str, Any]) -> None:
        reply_to = message.get("reply_to")
        correlation_id = message.get("correlation_id")
        if not reply_to or not correlation_id:
            return
        payload = message if isinstance(message, dict) else {}
        with state_lock:
            state_snapshot = dict(state)
        response = {
            "correlation_id": correlation_id,
            **_build_response_payload(payload, state_snapshot),
        }
        bus.publish(reply_to, response)
        print(f"[{client_id}] replied to {reply_to} for topic {topic}")

    def handle_set_home(message: Dict[str, Any]) -> None:
        payload = message.get("payload") if isinstance(message, dict) else None
        if not isinstance(payload, dict):
            return
        derived = payload.get("derived") if isinstance(payload.get("derived"), dict) else {}
        with state_lock:
            if derived.get("lat_decimal") is not None:
                state["lat"] = float(derived["lat_decimal"])
            if derived.get("lon_decimal") is not None:
                state["lon"] = float(derived["lon_decimal"])
            if derived.get("altitude_msl") is not None:
                alt = float(derived["altitude_msl"])
                state["alt"] = alt
                state["relative_alt"] = alt
            if payload.get("drone_id"):
                state["drone_id"] = str(payload["drone_id"])
        print(
            f"[{client_id}] updated HOME from set_home: "
            f"lat={state.get('lat')} lon={state.get('lon')} alt={state.get('alt')}"
        )

    def handle_sitl_control(message: Dict[str, Any]) -> None:
        if not isinstance(message, dict):
            return
        if any(key in message for key in ("vx", "vy", "vz", "mag_heading")):
            handle_sitl_command(message)
            return
        action = str(message.get("action") or "").strip().lower()
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}

        if action == "set_home":
            handle_set_home(message)
            return

        if action != "started_takeoff":
            return

        port_coordinates = payload.get("port_coordinates") if isinstance(payload.get("port_coordinates"), dict) else {}
        with state_lock:
            if port_coordinates.get("lat") is not None:
                state["lat"] = float(port_coordinates["lat"])
            if port_coordinates.get("lon") is not None:
                state["lon"] = float(port_coordinates["lon"])
            state["alt"] = 0.0
            state["relative_alt"] = 0.0
            state["vx"] = 0.0
            state["vy"] = 0.0
            state["vz"] = 0.0
            state["mode"] = "TAKEOFF_READY"
            if payload.get("battery") is not None:
                state["battery_pct"] = float(payload["battery"])
            if payload.get("drone_id"):
                state["drone_id"] = str(payload["drone_id"])
        print(
            f"[{client_id}] received started_takeoff: "
            f"lat={state.get('lat')} lon={state.get('lon')} battery={state.get('battery_pct')}"
        )

    def handle_sitl_command(message: Dict[str, Any]) -> None:
        if not isinstance(message, dict):
            return
        if not any(key in message for key in ("vx", "vy", "vz", "mag_heading")):
            return

        now = time.time()
        with state_lock:
            if message.get("drone_id"):
                state["drone_id"] = str(message["drone_id"])
            state["vx"] = float(message.get("vx") or 0.0)
            state["vy"] = float(message.get("vy") or 0.0)
            state["vz"] = float(message.get("vz") or 0.0)
            if message.get("mag_heading") is not None:
                state["yaw_deg"] = float(message["mag_heading"])
            state["mode"] = "GUIDED" if any(abs(float(message.get(k) or 0.0)) > 1e-6 for k in ("vx", "vy", "vz")) else "HOLD"
            state["last_command_ts"] = now
        print(
            f"[{client_id}] applied sitl command: "
            f"vx={message.get('vx', 0.0)} vy={message.get('vy', 0.0)} "
            f"vz={message.get('vz', 0.0)} heading={message.get('mag_heading')}"
        )

    def advance_state() -> None:
        now = time.time()
        with state_lock:
            last_update_ts = float(state.get("last_motion_update_ts") or now)
            dt_s = max(0.0, now - last_update_ts)
            state["last_motion_update_ts"] = now
            if dt_s <= 0.0:
                return

            last_command_ts = float(state.get("last_command_ts") or 0.0)
            if last_command_ts <= 0.0 or (now - last_command_ts) > command_hold_s:
                state["vx"] = 0.0
                state["vy"] = 0.0
                state["vz"] = 0.0
                if state.get("mode") == "GUIDED":
                    state["mode"] = "HOLD"
                return

            vx = float(state.get("vx") or 0.0)
            vy = float(state.get("vy") or 0.0)
            vz = float(state.get("vz") or 0.0)
            lat = float(state.get("lat") or 0.0)
            lon = float(state.get("lon") or 0.0)
            alt = float(state.get("alt") or 0.0)
            battery_pct = float(state.get("battery_pct") or 0.0)

            delta_lat, delta_lon = _meters_to_lat_lon_delta(vx, vy, lat, dt_s)
            new_alt = max(0.0, alt + (vz * dt_s))
            horizontal_speed = math.hypot(vx, vy)
            airborne = alt > 0.1 or new_alt > 0.1
            battery_drain = 0.0
            if airborne:
                battery_drain = dt_s * (
                    idle_drain_pct_per_s
                    + horizontal_speed * move_drain_pct_per_mps_s
                    + abs(vz) * vertical_drain_pct_per_mps_s
                )

            state["lat"] = lat + delta_lat
            state["lon"] = lon + delta_lon
            state["alt"] = new_alt
            state["relative_alt"] = new_alt
            state["battery_pct"] = max(0.0, min(100.0, battery_pct - battery_drain))

    def handle_signal(sig: int, _frame: Any) -> None:
        nonlocal running
        print(f"[{client_id}] received signal {sig}, shutting down")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        bus = None
        subscribed = False
        try:
            bus = create_system_bus(client_id=client_id)
            bus.start()
            bus.subscribe(topic, handle_request)
            bus.subscribe(sitl_topic, handle_sitl_control)
            if sitl_commands_topic != sitl_topic:
                bus.subscribe(sitl_commands_topic, handle_sitl_command)
            subscribed = True
            print(
                f"[{client_id}] SITL stub started. "
                f"Telemetry topic: {topic}; control topic: {sitl_topic}; commands topic: {sitl_commands_topic}"
            )

            while running:
                advance_state()
                time.sleep(tick_s)
        except Exception as exc:
            if not running:
                break
            print(
                f"[{client_id}] broker connection failed: {exc}. "
                f"Retrying in {retry_delay_s:.1f}s"
            )
            time.sleep(retry_delay_s)
        finally:
            if bus is not None:
                if subscribed:
                    try:
                        bus.unsubscribe(topic)
                    except Exception:
                        pass
                    try:
                        bus.unsubscribe(sitl_topic)
                    except Exception:
                        pass
                    try:
                        bus.unsubscribe(sitl_commands_topic)
                    except Exception:
                        pass
                try:
                    bus.stop()
                except Exception:
                    pass

    sys.exit(0)
