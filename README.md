# DronePort GCS

НУС/GCS для постановки задач дронам, подготовки миссий и передачи полетных команд через брокер сообщений.

README описывает внешний контракт системы: что должен знать эксплуатант, какие топики используются и какие сообщения реально поддерживаются в текущей реализации. Отдельно сохранен раздел по Дронопорту: он актуален, но его код еще отсутствует в текущем `main`.

## Содержание

- [Назначение](#назначение)
- [Дронопорт](#дронопорт)
- [Состав GCS](#состав-gcs)
- [Внешний контракт](#внешний-контракт)
- [Топики и адресация](#топики-и-адресация)
- [Протокол сообщений](#протокол-сообщений)
- [Интеграция с эксплуатантом](#интеграция-с-эксплуатантом)
- [Временный stub-канал дрона](#временный-stub-канал-дрона)
- [Хранимые сущности и статусы](#хранимые-сущности-и-статусы)
- [Запуск](#запуск)
- [Тесты](#тесты)
- [Структура репозитория](#структура-репозитория)

## Назначение

GCS принимает задачу от внешней системы эксплуатанта, строит маршрут, сохраняет миссию, конвертирует ее в `QGC WPL 110`, назначает миссию на конкретный борт и публикует команды в временный stub-канал:

- загрузить миссию;
- начать выполнение миссии;
- передавать телеметрию обратно в GCS для обновления состояния борта.

Поддерживаются два брокера:

- `MQTT`
- `Kafka`

В коде вся доменная логика GCS работает с dot-topic нотацией, например `v1.gcs.1.orchestrator`.
Для MQTT эта нотация автоматически преобразуется в slash-topic:

- внутренний топик: `v1.gcs.1.orchestrator`
- MQTT-топик: `v1/gcs/1/orchestrator`

## Дронопорт

Раздел сохранен по актуальной версии Дронопорта, но в текущей ветке его исходники и локальная документация еще отсутствуют. Поэтому это описание надо считать внешним контрактом и обзором подсистемы, а не ссылкой на присутствующий в репозитории код.

### Назначение

Дронопорт - сервис наземной инфраструктуры для приема, обслуживания и зарядки дронов.

Ключевые свойства:

- сервисно-ориентированная архитектура, взаимодействие с внешними системами только через брокер сообщений;
- отделение логики от состояния;
- возможность хранения состояния во внутреннем in-memory хранилище для прототипа или во внешнем хранилище для production;
- логирование критичных операций и валидация входящих сообщений.

### Поддерживаемые действия

В текущем описании Дронопорта используются следующие действия:

| Action | Payload | Ответ | Назначение |
|--------|---------|-------|------------|
| `REQUEST_LANDING` | `{"drone_id": str, "port_id": str, "battery_level": float}` | `{"status": "landed" \| "rejected", "drone_id": str, "port_id": str, "message": str}` | Регистрация дрона при посадке |
| `REQUEST_TAKEOFF` | `{"drone_id": str}` | `{"status": "takeoff_approved" \| "not_found", "drone_id": str, "battery_level": float}` | Освобождение площадки после взлета |
| `START_CHARGING` | `{"drone_id": str, "target_battery": float, "departure_time_sec": int}` | `{"status": "charging_started", "charging_power_w": float, "estimated_finish_sec": int}` | Запуск зарядки |
| `STOP_CHARGING` | `{"drone_id": str}` | `{"status": "charging_stopped", "drone_id": str}` | Остановка зарядки |
| `GET_PORT_STATUS` | `{"filter": "all" \| "landed" \| "charging"}` | `{"drones": [...], "total": int, "timestamp": float}` | Получение состояния дронопорта |

Пример ответа `GET_PORT_STATUS`:

```json
{
  "drones": [
    {
      "drone_id": "AGRO-042",
      "port_id": "PAD-03",
      "battery_level": 15.0,
      "status": "landed",
      "safety_target": "low_battery_alert",
      "issues": ["battery_critical"],
      "last_landing_time": 1739876543.123,
      "charging_power_w": 0.0
    }
  ],
  "total": 1,
  "timestamp": 1739876599.456
}
```

### Логические компоненты Дронопорта

В актуальном описании Дронопорт состоит из следующих подсистем:

- `DroneportOrchestrator` - маршрутизатор запросов от эксплуатанта.
- `DroneRegistry` - единый интерфейс к состоянию и операциям Дронопорта.
- `DroneManager` - взаимодействие с физическими дронами.
- `PortManager` - управление посадочными площадками.
- `ChargingManager` - управление процессом зарядки.
- `StateStore` - хранилище состояния.

Пока код Дронопорта не влит в `main`, этот раздел лучше использовать как продуктовый и интеграционный контур, а технические детали GCS ниже считать подтвержденными кодом этой ветки.

## Состав GCS

Система состоит из шести компонентов:

- `orchestrator` - внешняя точка входа для эксплуатанта.
- `path_planner` - строит маршрут по стартовой и конечной точке.
- `mission_store` - хранит миссии в Redis.
- `mission_converter` - преобразует маршрут в `QGC WPL 110`.
- `drone_manager` - публикует команды в текущий stub-канал борта и обновляет состояние миссии/борта.
- `drone_store` - хранит состояние дронов и последнюю телеметрию в Redis.

Актуальные C4-диаграммы лежат в [systems/gcs/docs/c4/README.md](/home/kaitrye/DronePortGCS/systems/gcs/docs/c4/README.md).

## Внешний контракт

Сейчас у GCS есть три интеграционных контура:

1. Эксплуатант публикует команды в `orchestrator`.
2. GCS публикует команды в отдельный топик `drone`, который сейчас используется как заглушка вместо реального борта.
3. Дрон, симулятор или telemetry-bridge публикует телеметрию в `drone_manager`.

Важно:

- полноценный request/response сейчас реализован только для `task.submit`;
- `task.assign` и `task.start` работают как `fire-and-forget`, синхронный ответ не возвращается;
- отдельного внешнего API для чтения миссий и состояния дронов в текущей реализации нет;
- топик `drone` не является целевым боевым интерфейсом, это временный stub-канал;
- `path_planner` пока строит stub-маршрут "туда и обратно" между двумя точками.

## Топики и адресация

Адресация GCS задается тремя переменными:

- `TOPIC_VERSION`, по умолчанию `v1`
- `GCS_SYSTEM_NAME`, по умолчанию `gcs`
- `INSTANCE_ID`, по умолчанию `1`

Формула внутренних топиков:

```text
<TOPIC_VERSION>.<GCS_SYSTEM_NAME>.<INSTANCE_ID>.<component>
```

При значениях по умолчанию используются такие топики:

| Назначение | Dot-topic | MQTT-topic |
|------------|-----------|------------|
| Эксплуатант -> Orchestrator | `v1.gcs.1.orchestrator` | `v1/gcs/1/orchestrator` |
| GCS -> PathPlanner | `v1.gcs.1.path_planner` | `v1/gcs/1/path_planner` |
| GCS -> MissionStore | `v1.gcs.1.mission_store` | `v1/gcs/1/mission_store` |
| GCS -> MissionConverter | `v1.gcs.1.mission_converter` | `v1/gcs/1/mission_converter` |
| GCS -> DroneManager | `v1.gcs.1.drone_manager` | `v1/gcs/1/drone_manager` |
| GCS -> DroneStore | `v1.gcs.1.drone_store` | `v1/gcs/1/drone_store` |
| GCS -> Drone stub | `drone` | `drone` |

Для внешних систем сейчас обычно нужны только:

- `v1.gcs.1.orchestrator`
- `v1.gcs.1.drone_manager`

Топик `drone` в этот список не включен как стабильная точка интеграции, потому что он временный.

## Протокол сообщений

Базовый формат сообщения:

```json
{
  "action": "task.submit",
  "payload": {},
  "sender": "external_system",
  "correlation_id": "corr-123",
  "reply_to": "optional.reply.topic",
  "timestamp": "2026-03-17T10:00:00+00:00"
}
```

Поля:

- `action` - обязательное действие.
- `payload` - обязательный объект с данными.
- `sender` - отправитель.
- `correlation_id` - рекомендован для трассировки цепочки.
- `reply_to` - обязателен только если нужен синхронный ответ.
- `timestamp` - можно не задавать вручную, но для внешних интеграций полезен.

Формат ответа на request:

```json
{
  "action": "response",
  "payload": {},
  "sender": "gcs_orchestrator",
  "correlation_id": "corr-123",
  "success": true,
  "timestamp": "2026-03-17T10:00:01+00:00"
}
```

При ошибке дополнительно приходит поле `error`.

## Интеграция с эксплуатантом

### 1. Постановка задачи

Топик:

- `v1.gcs.1.orchestrator`

Action:

- `task.submit`

Назначение:

- создать новую миссию;
- построить маршрут;
- сохранить миссию в `mission_store`;
- вернуть `mission_id`, маршрут и подпись маршрута.

Минимальный запрос:

```json
{
  "action": "task.submit",
  "sender": "operator_system",
  "correlation_id": "corr-submit-001",
  "reply_to": "operator/replies",
  "payload": {
    "task_type": "delivery",
    "start_point": {
      "lat": 55.751244,
      "lon": 37.618423,
      "alt": 120
    },
    "end_point": {
      "lat": 55.761244,
      "lon": 37.628423,
      "alt": 130
    }
  }
}
```

Успешный ответ:

```json
{
  "action": "response",
  "sender": "gcs_orchestrator",
  "correlation_id": "corr-submit-001",
  "success": true,
  "payload": {
    "from": "gcs_orchestrator",
    "mission_id": "m-abcdef123456",
    "waypoints": [
      {"lat": 55.751244, "lon": 37.618423, "alt": 120.0},
      {"lat": 55.754544, "lon": 37.621723, "alt": 123.3},
      {"lat": 55.757844, "lon": 37.625023, "alt": 126.6},
      {"lat": 55.761244, "lon": 37.628423, "alt": 130.0},
      {"lat": 55.757944, "lon": 37.625123, "alt": 126.7},
      {"lat": 55.754644, "lon": 37.621823, "alt": 123.4},
      {"lat": 55.751244, "lon": 37.618423, "alt": 120.0}
    ],
    "signature": "sha256_of_waypoints"
  }
}
```

Ответ при ошибке:

```json
{
  "action": "response",
  "sender": "gcs_orchestrator",
  "correlation_id": "corr-submit-001",
  "success": true,
  "payload": {
    "from": "gcs_orchestrator",
    "error": "failed to build route"
  }
}
```

Замечание: на уровне бизнес-логики ошибка маршрута сейчас возвращается внутри `payload`, а не через `success=false`.

### 2. Назначение миссии на дрон

Топик:

- `v1.gcs.1.orchestrator`

Action:

- `task.assign`

Назначение:

- взять уже сохраненную миссию по `mission_id`;
- преобразовать маршрут в `WPL`;
- опубликовать команду загрузки миссии в временный stub-топик `drone`;
- перевести миссию в статус `assigned`;
- перевести дрон в статус `reserved`.

Сообщение:

```json
{
  "action": "task.assign",
  "sender": "operator_system",
  "correlation_id": "corr-assign-001",
  "payload": {
    "mission_id": "m-abcdef123456",
    "drone_id": "drone-01"
  }
}
```

Синхронный ответ не предусмотрен. Подтверждение нужно отслеживать косвенно:

- по сообщению `drone.upload_mission` в stub-топике `drone`;
- по внутреннему состоянию миссии и дрона.

### 3. Старт миссии

Топик:

- `v1.gcs.1.orchestrator`

Action:

- `task.start`

Назначение:

- отправить дрону команду старта миссии;
- перевести миссию в `running`;
- перевести дрон в `BUSY`.

Сообщение:

```json
{
  "action": "task.start",
  "sender": "operator_system",
  "correlation_id": "corr-start-001",
  "payload": {
    "mission_id": "m-abcdef123456",
    "drone_id": "drone-01"
  }
}
```

Синхронный ответ не предусмотрен.

## Временный stub-канал дрона

Топик `drone` в текущей реализации используется как заглушка вместо настоящего канала связи с дроном. Этот интерфейс не стоит считать целевым внешним контрактом на будущее: он нужен для текущей разработки, тестов и эмуляции борта.

### Сообщения, которые GCS публикует в stub-топик

Топик:

- `drone`

#### 1. Загрузка миссии

Action:

- `drone.upload_mission`

Сообщение:

```json
{
  "action": "drone.upload_mission",
  "sender": "gcs_drone_manager",
  "correlation_id": "corr-assign-001",
  "payload": {
    "mission_id": "m-abcdef123456",
    "mission": "QGC WPL 110\n0\t1\t3\t16\t0\t0\t0\t0\t55.751244\t37.618423\t120.0\t1\n1\t0\t3\t16\t0\t0\t0\t0\t55.754544\t37.621723\t123.3\t1"
  }
}
```

Поле `mission` - это строка в формате `QGC WPL 110`.

Формат строки WPL, который генерирует GCS:

```text
QGC WPL 110
<seq> <current> <frame> <command> <p1> <p2> <p3> <p4> <lat> <lon> <alt> <autocontinue>
```

Сейчас по умолчанию:

- первая точка идет с `current=1`, остальные с `current=0`;
- `frame=3`;
- `command=16`;
- `autocontinue=1`;
- параметры `p1...p4` берутся из `point.params`, если они были переданы, иначе `0`.

#### 2. Старт миссии

Action:

- `drone.mission.start`

Сообщение:

```json
{
  "action": "drone.mission.start",
  "sender": "gcs_drone_manager",
  "correlation_id": "corr-start-001",
  "payload": {}
}
```

Важно: в текущей реализации `mission_id` и `drone_id` в payload этой команды не передаются. Если дрону или внешнему bridge нужен этот контекст, его надо восстанавливать по `correlation_id` или расширять контракт в коде.

### Телеметрия, которую GCS принимает от дрона или симулятора

Топик:

- `v1.gcs.1.drone_manager`

Action:

- `telemetry.save`

Минимальное сообщение:

```json
{
  "action": "telemetry.save",
  "sender": "drone_adapter",
  "correlation_id": "corr-telemetry-001",
  "payload": {
    "telemetry": {
      "drone_id": "drone-01",
      "battery": 87,
      "latitude": 55.751244,
      "longitude": 37.618423,
      "altitude": 120
    }
  }
}
```

Что делает GCS:

- сохраняет состояние дрона в `drone_store`;
- обновляет `battery`, если поле присутствует;
- обновляет `last_position`, если пришли `latitude` и `longitude`;
- если дрон ранее не был зарегистрирован, создает запись и выставляет базовый статус `connected`.

Синхронный ответ не предусмотрен.

## Хранимые сущности и статусы

### Миссия

Миссия хранится в Redis и содержит как минимум:

```json
{
  "mission_id": "m-abcdef123456",
  "waypoints": [],
  "signature": "sha256",
  "status": "created",
  "assigned_drone": null,
  "created_at": "2026-03-17T10:00:00+00:00",
  "updated_at": "2026-03-17T10:00:00+00:00"
}
```

Статусы миссии:

- `created`
- `assigned`
- `running`

### Дрон

Состояние дрона хранится в Redis и может содержать:

```json
{
  "status": "reserved",
  "battery": 87,
  "connected_at": "2026-03-17T10:00:00+00:00",
  "last_position": {
    "latitude": 55.751244,
    "longitude": 37.618423,
    "altitude": 120
  }
}
```

Статусы дрона, используемые GCS:

- `connected` - создан по первой телеметрии;
- `available` - предусмотрен моделью и индексом хранилища;
- `reserved` - миссия назначена, но еще не стартовала;
- `BUSY` - миссия запущена.

Важно: в коде статус `BUSY` хранится именно в верхнем регистре.

## Запуск

### Требования

- Docker + Docker Compose
- Python `>= 3.12`
- `pipenv`

### 1. Поднять брокерную инфраструктуру

```bash
cp docker/example.env docker/.env
make docker-up
```

По умолчанию в [docker/example.env](/home/kaitrye/DronePortGCS/docker/example.env) стоит:

- `BROKER_TYPE=mqtt`
- `INSTANCE_ID=1`

### 2. Поднять GCS

```bash
cd systems/gcs
make docker-up
```

Команда:

- соберет `systems/gcs/.generated/docker-compose.yml`;
- сгенерирует `systems/gcs/.generated/.env`;
- поднимет `redis`, `mission_store`, `drone_store`, `mission_converter`, `orchestrator`, `path_planner`, `drone_manager` вместе с выбранным брокером.

Если нужен только prepare:

```bash
cd systems/gcs
make prepare
```

### Основные переменные окружения

| Переменная | Значение по умолчанию | Назначение |
|------------|------------------------|------------|
| `BROKER_TYPE` | `mqtt` | Тип брокера: `mqtt` или `kafka` |
| `INSTANCE_ID` | `1` | Идентификатор экземпляра GCS |
| `TOPIC_VERSION` | `v1` | Версия префикса топиков |
| `GCS_SYSTEM_NAME` | `gcs` | Имя системы в адресации |
| `MQTT_BROKER` | `mosquitto` / `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka bootstrap servers |
| `BROKER_USER` | из `ADMIN_USER` | Логин брокера |
| `BROKER_PASSWORD` | из `ADMIN_PASSWORD` | Пароль брокера |
| `MISSION_STORE_REDIS_DB` | `0` | Redis DB для миссий |
| `DRONE_STORE_REDIS_DB` | `1` | Redis DB для дронов |

## Тесты

Все тесты:

```bash
make tests
```

Только unit:

```bash
make unit-test
```

Только интеграционные:

```bash
make integration-test
```

Системные тесты GCS лежат в:

- [systems/gcs/tests/unit/test_orchestrator.py](/home/kaitrye/DronePortGCS/systems/gcs/tests/unit/test_orchestrator.py)
- [systems/gcs/tests/unit/test_drone_manager.py](/home/kaitrye/DronePortGCS/systems/gcs/tests/unit/test_drone_manager.py)
- [systems/gcs/tests/integration/test_gcs_integration.py](/home/kaitrye/DronePortGCS/systems/gcs/tests/integration/test_gcs_integration.py)

## Структура репозитория

```text
broker/                 Шина сообщений и фабрика брокеров
sdk/                    BaseComponent, BaseSystem, message protocol
docker/                 Общая инфраструктура Kafka/MQTT
scripts/                Генерация compose-файлов систем
systems/gcs/            Исходный код НУС/GCS
systems/gcs/src/
  orchestrator/         Внешняя точка входа для эксплуатанта
  path_planner/         Построение маршрута
  mission_store/        Хранилище миссий
  mission_converter/    Конвертация маршрута в WPL
  drone_manager/        Публикация команд в stub-канал и прием телеметрии
  drone_store/          Хранилище состояния дронов
```

## Что еще важно внешним системам

- Если интеграция идет по MQTT, используйте slash-topic форму, например `v1/gcs/1/orchestrator`.
- Если нужен синхронный ответ, обязательно передавайте `reply_to`.
- Для `task.assign`, `task.start` и `telemetry.save` текущая реализация не возвращает response.
- Топик `drone` сейчас является только заглушкой и не должен использоваться как долгосрочный внешний контракт.
- Контракт чтения миссий/дронов наружу пока не выделен в отдельный API.
- `path_planner` пока не использует реальную картографию и ограничения полета, а строит stub-маршрут по двум точкам.
