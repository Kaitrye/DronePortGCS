"""Tests for sdk.security_journal — JournalRecorder + JournalRecord."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

import pytest

from sdk.security_journal import (
    LOG_EVENT_ACTION,
    MAX_MESSAGE_LEN,
    SEVERITY_LEVELS,
    SEVERITY_RANK,
    JournalRecord,
    JournalRecorder,
)


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _make_recorder(tmp_path: Path, **overrides) -> tuple[JournalRecorder, Path]:
    file_path = tmp_path / "journal.ndjson"
    kwargs = dict(file_path=str(file_path), service="dronePort", service_id=1)
    kwargs.update(overrides)
    return JournalRecorder(**kwargs), file_path


def test_log_event_action_constant():
    assert LOG_EVENT_ACTION == "log_event"


def test_severity_levels_order_matches_syslog():
    assert SEVERITY_LEVELS == (
        "debug", "info", "notice", "warning", "error",
        "critical", "alert", "emergency",
    )
    assert SEVERITY_RANK["debug"] < SEVERITY_RANK["emergency"]


def test_write_appends_valid_ndjson(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    record = recorder.build_record(
        severity="warning",
        source_sender="components.drone_manager",
        source_component="drone_manager",
        source_action="request_landing.no_free_ports",
        message="Landing denied",
        details={"drone_id": "DR-1"},
    )
    assert record is not None
    recorder.write(record)

    lines = _read_lines(file_path)
    assert len(lines) == 1
    entry = lines[0]
    assert entry["severity"] == "warning"
    assert entry["service"] == "dronePort"
    assert entry["service_id"] == 1
    assert entry["event_type"] == "safety_event"
    assert entry["source_component"] == "drone_manager"
    assert entry["source_action"] == "request_landing.no_free_ports"
    assert entry["details"] == {"drone_id": "DR-1"}
    assert isinstance(entry["timestamp_ms"], int)
    assert entry["timestamp_iso"].endswith("+00:00")


def test_log_helper_writes_one_line(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    recorder.log(
        severity="critical",
        source_sender="systems.drone_port",
        source_component="drone_port_security_monitor",
        source_action="proxy_request.denied",
        message="Policy denied",
        details={"target_action": "request_landing"},
    )
    lines = _read_lines(file_path)
    assert len(lines) == 1
    assert lines[0]["severity"] == "critical"


def test_invalid_severity_drops_record(tmp_path, caplog):
    recorder, _ = _make_recorder(tmp_path)
    with caplog.at_level(logging.WARNING):
        record = recorder.build_record(
            severity="VERY-BAD",
            source_sender="x",
            source_component="x",
            source_action="x",
            message="x",
        )
    assert record is None
    assert "invalid severity" in caplog.text


def test_min_severity_filter_skips_below(tmp_path):
    recorder, file_path = _make_recorder(tmp_path, min_severity="warning")
    recorder.log(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="should be skipped",
    )
    recorder.log(
        severity="warning",
        source_sender="s", source_component="c", source_action="a",
        message="kept",
    )
    recorder.log(
        severity="critical",
        source_sender="s", source_component="c", source_action="a",
        message="kept",
    )
    lines = _read_lines(file_path)
    assert [entry["severity"] for entry in lines] == ["warning", "critical"]


def test_message_truncated_to_max_len(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    big = "x" * (MAX_MESSAGE_LEN + 500)
    recorder.log(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message=big,
    )
    entry = _read_lines(file_path)[0]
    assert len(entry["message"]) == MAX_MESSAGE_LEN


def test_concurrent_writes_serialize(tmp_path):
    recorder, file_path = _make_recorder(tmp_path)
    threads_n = 8
    per_thread = 25

    def worker(idx: int) -> None:
        for n in range(per_thread):
            recorder.log(
                severity="info",
                source_sender="s",
                source_component="c",
                source_action=f"t{idx}.n{n}",
                message=f"thread {idx} item {n}",
            )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = _read_lines(file_path)
    assert len(lines) == threads_n * per_thread
    # Каждая строка — самостоятельный валидный JSON (значит запись была атомарной).
    for entry in lines:
        assert "source_action" in entry


def test_io_error_does_not_raise(tmp_path, monkeypatch, caplog):
    recorder, _ = _make_recorder(tmp_path)
    record = recorder.build_record(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="m",
    )
    assert record is not None

    def _boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", _boom)
    with caplog.at_level(logging.ERROR):
        recorder.write(record)  # must not raise
    assert "journal: write failed" in caplog.text


def test_empty_file_path_is_no_op(tmp_path):
    recorder = JournalRecorder(file_path="", service="dronePort", service_id=1)
    record = recorder.build_record(
        severity="info",
        source_sender="s", source_component="c", source_action="a",
        message="m",
    )
    assert record is not None
    recorder.write(record)  # must not raise, must not create files
    assert not any(tmp_path.iterdir())


def test_dataclass_default_event_type():
    rec = JournalRecord(
        timestamp_iso="t", timestamp_ms=0,
        service="GCS", service_id=2,
        severity="info", message="m",
        source_component="c", source_sender="s", source_action="a",
    )
    assert rec.event_type == "safety_event"
    assert rec.details == {}


def test_creates_parent_dir(tmp_path):
    nested = tmp_path / "a" / "b" / "journal.ndjson"
    recorder = JournalRecorder(file_path=str(nested), service="GCS", service_id=2)
    recorder.log(
        severity="notice",
        source_sender="s", source_component="c", source_action="port.reserved",
        message="ok",
    )
    assert nested.exists()
    assert _read_lines(nested)[0]["service"] == "GCS"


# ---------- InfopanelDispatcher ----------

import threading

from sdk.security_journal import InfopanelDispatcher


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    """Drop-in replacement for requests.Session used by the dispatcher."""

    def __init__(self, responses=None, raise_first=0):
        # responses: list of FakeResponse to cycle through; default 200 OK
        self._responses = list(responses or [FakeResponse(200)])
        self._raise_first = raise_first
        self.calls = []
        self.headers = {}
        self._lock = threading.Lock()

    def post(self, url, json=None, timeout=None, verify=None):
        with self._lock:
            self.calls.append({"url": url, "json": json, "timeout": timeout, "verify": verify})
            if self._raise_first > 0:
                self._raise_first -= 1
                raise ConnectionError("simulated network error")
            if not self._responses:
                return FakeResponse(200)
            if len(self._responses) == 1:
                return self._responses[0]
            return self._responses.pop(0)


def _make_record(severity="warning", source_action="x.action", message="m"):
    return JournalRecord(
        timestamp_iso="2026-05-03T12:00:00.000+00:00",
        timestamp_ms=1746275600000,
        service="dronePort",
        service_id=1,
        severity=severity,
        message=message,
        source_component="drone_manager",
        source_sender="components.drone_manager",
        source_action=source_action,
        details={},
    )


def test_dispatcher_disabled_when_url_or_key_missing():
    d1 = InfopanelDispatcher(url="", api_key="k")
    d2 = InfopanelDispatcher(url="https://x", api_key="")
    d1.enqueue(_make_record())
    d2.enqueue(_make_record())
    assert d1._queue.qsize() == 0
    assert d2._queue.qsize() == 0


def test_dispatcher_sends_batch_with_api_key_header():
    fake = FakeSession([FakeResponse(200)])
    d = InfopanelDispatcher(
        url="https://infopanel.example/api/log/event",
        api_key="secret-key",
        batch_size=10,
        flush_interval_s=0.05,
        session=fake,
    )
    # set api key into fake session as the dispatcher would on real session
    fake.headers["X-API-Key"] = "secret-key"

    for sev in ("info", "warning", "critical"):
        d.enqueue(_make_record(severity=sev, source_action=f"x.{sev}"))

    d.start()
    # wait for at least one POST
    for _ in range(50):
        if fake.calls:
            break
        time.sleep(0.05)
    d.stop()

    assert fake.calls, "dispatcher did not POST"
    sent = fake.calls[-1]
    assert sent["url"] == "https://infopanel.example/api/log/event"
    assert sent["verify"] is True
    payload = sent["json"]
    assert isinstance(payload, list) and len(payload) >= 1
    item = payload[0]
    assert item["apiVersion"] == "1.1.0"
    assert item["event_type"] == "safety_event"
    assert item["service"] == "dronePort"
    assert item["service_id"] == 1
    assert item["severity"] in {"info", "warning", "critical"}
    assert isinstance(item["timestamp"], int)


import time  # noqa: E402  (used above)


def test_dispatcher_retries_on_5xx_then_succeeds():
    fake = FakeSession([FakeResponse(503), FakeResponse(200)])
    d = InfopanelDispatcher(
        url="https://x", api_key="k",
        batch_size=10, flush_interval_s=0.05,
        max_retries=3, retry_backoff_s=0.01,
        session=fake,
    )
    d.enqueue(_make_record())
    d.start()
    for _ in range(50):
        if len(fake.calls) >= 2:
            break
        time.sleep(0.05)
    d.stop()
    assert len(fake.calls) >= 2  # 1 retry after 503, then success


def test_dispatcher_does_not_retry_on_4xx():
    fake = FakeSession([FakeResponse(401, text="Unauthorized")])
    d = InfopanelDispatcher(
        url="https://x", api_key="bad",
        batch_size=10, flush_interval_s=0.05,
        max_retries=3, retry_backoff_s=0.01,
        session=fake,
    )
    d.enqueue(_make_record())
    d.start()
    for _ in range(20):
        if fake.calls:
            break
        time.sleep(0.05)
    # give it a moment to confirm no retry happens
    time.sleep(0.1)
    d.stop()
    assert len(fake.calls) == 1


def test_dispatcher_drops_oldest_when_queue_full():
    d = InfopanelDispatcher(
        url="https://x", api_key="k",
        queue_max=2, session=FakeSession(),
    )
    r1, r2, r3 = (_make_record(source_action=f"x.{i}") for i in range(1, 4))
    d.enqueue(r1)
    d.enqueue(r2)
    d.enqueue(r3)  # should drop r1
    assert d._queue.qsize() == 2
    items = []
    while not d._queue.empty():
        items.append(d._queue.get_nowait())
    actions = {r.source_action for r in items}
    assert "x.1" not in actions
    assert {"x.2", "x.3"}.issubset(actions)


def test_dispatcher_stop_is_idempotent_and_drains_quickly():
    d = InfopanelDispatcher(
        url="https://x", api_key="k",
        flush_interval_s=0.05, session=FakeSession(),
    )
    d.start()
    d.stop()
    d.stop()  # second call must not raise


def test_journal_recorder_with_sink_enqueues():
    fake = FakeSession()
    d = InfopanelDispatcher(url="https://x", api_key="k", session=fake)
    recorder = JournalRecorder(
        file_path="",  # no NDJSON, only sink
        service="dronePort", service_id=1,
        sink=d,
    )
    recorder.log(
        severity="warning",
        source_sender="s", source_component="c", source_action="a",
        message="m",
    )
    assert d._queue.qsize() == 1


def test_record_to_infopanel_item_shape():
    r = _make_record(severity="critical", source_action="proxy_request.denied", message="x" * 2000)
    item = r.to_infopanel_item()
    assert set(item.keys()) == {"apiVersion", "timestamp", "event_type", "service", "service_id", "severity", "message"}
    assert len(item["message"]) == MAX_MESSAGE_LEN
    assert item["timestamp"] == r.timestamp_ms
    assert item["severity"] == "critical"
