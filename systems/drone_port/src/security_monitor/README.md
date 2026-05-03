# Security Monitor (Drone Port) — журнал безопасности

Помимо проверки политик доступа (`proxy_request` / `proxy_publish`), этот компонент ведёт **журнал безопасности** в формате NDJSON. Все компоненты Дронопорта пишут в журнал через монитор безопасности.

## Как другие компоненты пишут в журнал

В любом методе `_handle_*` (унаследовано от `BaseComponent`):

```python
self._log_security(
    severity="warning",
    source_action="request_landing.no_free_ports",
    message=f"Landing denied for drone {drone_id}: no free ports",
    details={"drone_id": drone_id, "model": model, "battery": battery},
)
```

Helper `_log_security` публикует одно сообщение `action="log_event"` в топик security_monitor (env `SECURITY_MONITOR_TOPIC`). Если переменная не задана — вызов no-op. Никогда не блокирует и не бросает исключений.

## Severity-уровни

8 syslog-совместимых, форвард-совместимы с Инфопанелью :

| Уровень       | Когда применять                                                                          |
|---------------|------------------------------------------------------------------------------------------|
| `debug`       | (по умолчанию отсечён фильтром) детальная отладка                                        |
| `info`        | входящие запросы (`request_landing.received`, `request_takeoff.received`, `port.request_landing.received`, `charging.start_requested`, `state_store.update_port.received`, `registry.register_requested`, `get_available_drones.received`) |
| `notice`      | штатные изменения состояния (порт зарезервирован/освобождён, дрон зарегистрирован, зарядка стартовала/завершилась) |
| `warning`     | бизнес-отказ при валидном запросе (low_battery, no_free_ports, invalid payload)          |
| `error`       | технический сбой (bus.request → no response, redis exception, registry failed)           |
| `critical`    | security policy violation (`proxy_request.denied`, `proxy_publish.denied`)               |
| `alert`       | невалидная схема `proxy_request`/`proxy_publish` от внутреннего компонента               |
| `emergency`   | зарезервировано для аварийной остановки                                                  |

## Схема записи (NDJSON)

```jsonc
{
  "timestamp_iso":     "2026-05-03T12:34:56.789+00:00",
  "timestamp_ms":      1746275696789,
  "service":           "dronePort",
  "service_id":        1,
  "event_type":        "safety_event",
  "severity":          "warning",
  "message":           "Landing denied: no free ports",
  "source_component":  "drone_port",
  "source_sender":     "components.drone_manager",
  "source_action":     "request_landing.no_free_ports",
  "details":           { "drone_id": "DR-1", "battery": 25 }
}
```

Поля `timestamp_ms`, `service`, `service_id`, `event_type`, `severity`, `message` соответствуют контракту Инфопанели `POST /log/event` - отправка батчами добавляется отдельным шагом без изменения схемы.

## Env-переменные

| Переменная                          | По умолчанию                                  | Назначение |
|-------------------------------------|------------------------------------------------|------------|
| `SECURITY_JOURNAL_FILE_PATH`        | `/var/log/drones/security_journal.ndjson`     | путь к NDJSON-файлу |
| `SECURITY_JOURNAL_MIN_SEVERITY`     | `info`                                         | минимальный уровень для записи |
| `SECURITY_JOURNAL_SERVICE_ID`       | `1`                                            | id экземпляра дронопорта (1..1000) |
| `SECURITY_MONITOR_TOPIC` *(в источниках)* | `systems.drone_port`                     | куда `_log_security` публикует |

## Smoke-тест

```bash
docker compose --profile mqtt up -d
# отправить заведомо отказной landing (нет свободных портов)
docker compose exec security_monitor tail -f /var/log/drones/security_journal.ndjson
```
