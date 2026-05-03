"""Security journal: structured NDJSON-on-disk recorder with severity levels.

Schema is forward-compatible with Infopanel /log/event API (team 4):
fields ``timestamp_ms``, ``service``, ``service_id``, ``event_type``,
``severity`` and ``message`` mirror that contract. Local-only fields
``source_component``, ``source_sender``, ``source_action`` and ``details``
stay in the NDJSON file for diagnostics and are not sent over the wire.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


SEVERITY_LEVELS = (
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
)
SEVERITY_RANK = {level: index for index, level in enumerate(SEVERITY_LEVELS)}

LOG_EVENT_ACTION = "log_event"

MAX_MESSAGE_LEN = 1024


@dataclass
class JournalRecord:
    timestamp_iso: str
    timestamp_ms: int
    service: str
    service_id: int
    severity: str
    message: str
    source_component: str
    source_sender: str
    source_action: str
    details: Dict[str, Any] = field(default_factory=dict)
    event_type: str = "safety_event"

    def to_ndjson_line(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False) + "\n"


class JournalRecorder:
    """Append-only NDJSON writer with severity filter. Thread-safe."""

    def __init__(
        self,
        file_path: str,
        *,
        min_severity: str = "info",
        service: str = "",
        service_id: int = 1,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._file_path = file_path
        self._service = service
        self._service_id = int(service_id)
        self._logger = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._min_rank = SEVERITY_RANK.get(min_severity.lower(), SEVERITY_RANK["info"])

        if file_path:
            directory = os.path.dirname(file_path)
            if directory:
                try:
                    os.makedirs(directory, exist_ok=True)
                except OSError as exc:
                    self._logger.error("journal: cannot create dir %s: %s", directory, exc)

    def build_record(
        self,
        *,
        severity: str,
        source_sender: str,
        source_component: str,
        source_action: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[JournalRecord]:
        sev = (severity or "").lower().strip()
        rank = SEVERITY_RANK.get(sev)
        if rank is None:
            self._logger.warning("journal: invalid severity %r, dropping event %r", severity, source_action)
            return None
        if rank < self._min_rank:
            return None

        now = datetime.now(timezone.utc)
        return JournalRecord(
            timestamp_iso=now.isoformat(timespec="milliseconds"),
            timestamp_ms=int(now.timestamp() * 1000),
            service=self._service,
            service_id=self._service_id,
            severity=sev,
            message=(message or "")[:MAX_MESSAGE_LEN],
            source_component=source_component or "",
            source_sender=source_sender or "",
            source_action=source_action or "",
            details=details or {},
        )

    def write(self, record: JournalRecord) -> None:
        if not self._file_path:
            return
        line = record.to_ndjson_line()
        with self._lock:
            try:
                with open(self._file_path, "a", encoding="utf-8") as fh:
                    fh.write(line)
            except OSError as exc:
                self._logger.error(
                    "journal: write failed (%s): %s | record=%s",
                    self._file_path,
                    exc,
                    line.rstrip("\n"),
                )

    def log(
        self,
        *,
        severity: str,
        source_sender: str,
        source_component: str,
        source_action: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = self.build_record(
            severity=severity,
            source_sender=source_sender,
            source_component=source_component,
            source_action=source_action,
            message=message,
            details=details,
        )
        if record is not None:
            self.write(record)


__all__ = [
    "SEVERITY_LEVELS",
    "SEVERITY_RANK",
    "LOG_EVENT_ACTION",
    "MAX_MESSAGE_LEN",
    "JournalRecord",
    "JournalRecorder",
]
