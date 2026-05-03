# Security Monitor (GCS / НУС) — журнал безопасности

Помимо проверки политик доступа (`proxy_request` / `proxy_publish`), этот компонент ведёт **журнал безопасности** в формате NDJSON. Все компоненты НУС пишут в журнал через монитор безопасности.

## Как другие компоненты пишут в журнал

В любом методе `_handle_*` (унаследовано от `BaseComponent`):

```python
self._log_security(
    severity="error",
    source_action="mission_start.failed",
    message=f"Mission {mission_id} failed to start on drone {drone_id}",
    details={"mission_id": mission_id, "drone_id": drone_id},
)
```

Helper `_log_security` публикует одно сообщение `action="log_event"` в топик security_monitor (env `SECURITY_MONITOR_TOPIC`). Если переменная не задана - вызов no-op. Никогда не блокирует и не бросает исключений.

## Severity-уровни

8 syslog-совместимых, форвард-совместимы с Инфопанелью команды 4:

| Уровень       | Когда применять                                                                          |
|---------------|------------------------------------------------------------------------------------------|
| `debug`       | (по умолчанию отсечён фильтром) детальная отладка                                        |
| `info`        | входящие запросы (`task_submit.received`, `task_assign.received`, `task_start.received`, `mission_upload.received`, `mission_start.received`) |
| `notice`      | штатные изменения состояния (task_submit/assign/start approved, mission uploaded)        |
| `warning`     | бизнес-отказ при валидном запросе (failed to build route, mission_prepare_failed)        |
| `error`       | технический сбой (bus.request → no response, mission_start_failed)                       |
| `critical`    | security policy violation (`proxy_request.denied`, `proxy_publish.denied`)               |
| `alert`       | невалидная схема `proxy_request`/`proxy_publish` от внутреннего компонента               |
| `emergency`   | зарезервировано для аварийной остановки                                                  |

## Схема записи (NDJSON)

```jsonc
{
  "timestamp_iso":     "2026-05-03T12:34:56.789+00:00",
  "timestamp_ms":      1746275696789,
  "service":           "GCS",
  "service_id":        1,
  "event_type":        "safety_event",
  "severity":          "error",
  "message":           "Mission m-7af failed to start on drone DR-1",
  "source_component":  "gcs_drone_manager",
  "source_sender":     "components.drone_manager",
  "source_action":     "mission_start.failed",
  "details":           { "mission_id": "m-7af", "drone_id": "DR-1" }
}
```

Поля `timestamp_ms`, `service`, `service_id`, `event_type`, `severity`, `message` соответствуют контракту Инфопанели `POST /log/event` — отправка батчами добавляется отдельным шагом без изменения схемы.

## Env-переменные

| Переменная                          | По умолчанию                                  | Назначение |
|-------------------------------------|------------------------------------------------|------------|
| `SECURITY_JOURNAL_FILE_PATH`        | `/var/log/drones/security_journal.ndjson`     | путь к NDJSON-файлу |
| `SECURITY_JOURNAL_MIN_SEVERITY`     | `info`                                         | минимальный уровень для записи |
| `SECURITY_JOURNAL_SERVICE_ID`       | `1`                                            | id экземпляра НУС (1..1000) |
| `SECURITY_MONITOR_TOPIC` *(в источниках)* | `systems.gcs`                            | куда `_log_security` публикует |

## Smoke-тест

```bash
docker compose --profile mqtt up -d
# отправить task_submit без валидной задачи → planner вернёт ошибку
docker compose exec security_monitor tail -f /var/log/drones/security_journal.ndjson
```
