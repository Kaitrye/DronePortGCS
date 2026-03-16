# droneport-navigation-system


## Оглавление
- [Дронопорт](#дронопорт)
  - [Назначение](#назначение)
  - [Поддерживаемые действия](#поддерживаемые-действия)
  - [Компоненты](#компоненты)
    - [DroneportOrchestrator](#droneportOrchestrator)
    - [DroneRegistry](#droneRegistry)
    - [DroneManager](#droneManager)
    - [PortManager](#portManager)
    - [ChargingManager](#chargingManager)
    - [StateStore](#stateStore)
- [Наземная управляющая станция](#наземная-управляющая-станция)
  - [Обзор системы](#обзор-системы)
  - [Архитектура](#архитектура)
    - [Контекст системы](#контекст-системы)
    - [Контейнеры](#контейнеры)
    - [Уровни доверия](#уровни-доверия)
  - [Ключевые компоненты](#ключевые-компоненты)
- [Быстрый старт](#быстрый-старт)
  - [Предварительные требования](#предварительные-требования)
  - [Настройка окружения](#настройка-окружения)
  - [Запуск инфраструктуры](#запуск-инфраструктуры)
  - [Выполнение тестов](#выполнение-тестов)
- [Общение между компонентами](#общение-между-компонентами)
- [Структура репозитория](#структура-репозитория)
- [Технологический стек](#технологический-стек)

## Дронопорт

Дронопорт — сервис наземной инфраструктуры для приёма, обслуживания и зарядки агродронов. 
- **Сервисно-ориентированная архитектура** (требование А2 ТЗ): дронопорт — независимый сервис, взаимодействующий с другими системами **только через брокер сообщений** (`SystemBus`).
- **Stateless-логика**: бизнес-логика отделена от состояния. Состояние (список дронов, площадок) хранится во внутреннем in-memory хранилище (для прототипа) или может быть вынесено в Redis/PostgreSQL (для production).
- **СКИБ-совместимость**: все входящие сообщения проходят валидацию, ответы содержат коды ошибок, логируются критические операции (посадка/взлёт).
[Подробнее о дронопорте](./systems/drone_port/docs/droneport_description.md)

### Назначение

Система реализует функциональные требования к дронопорту:

| Требование | Описание |
|------------|----------|
| **ОФ1** | Приём дронов: проверка запроса посадки, регистрация дрона в парке, контроль занятости посадочных площадок |
| **ОФ2** | Обслуживание дронов: подготовка к вылету, освобождение площадки после взлёта |
| **ОФ3** | Генерация списка дронов: формирование актуального реестра всех дронов в дронопорту с их состоянием |
| **ОФ4** | Диагностика: мониторинг уровня заряда батареи, выявление неисправностей, формирование целей безопасности |
| **ПРФ1** | Оптимизация зарядки: расчёт мощности зарядки с учётом времени вылета и технических ограничений |

---

### Поддерживаемые действия

Все действия публикуются в топик `systems.droneport` (см. `shared/topics.py` → `DroneportActions`).

| Action | Payload | Ответ | Назначение |
|--------|---------|-------|------------|
| `REQUEST_LANDING` | `{"drone_id": str, "port_id": str, "battery_level": float}` | `{"status": "landed"\|"rejected", "drone_id": str, "port_id": str, "message": str}` | Регистрация дрона при посадке |
| `REQUEST_TAKEOFF` | `{"drone_id": str}` | `{"status": "takeoff_approved"\|"not_found", "drone_id": str, "battery_level": float}` | Освобождение площадки после взлёта |
| `START_CHARGING` | `{"drone_id": str, "target_battery": float, "departure_time_sec": int}` | `{"status": "charging_started", "charging_power_w": float, "estimated_finish_sec": int}` | Запуск оптимизированной зарядки |
| `STOP_CHARGING` | `{"drone_id": str}` | `{"status": "charging_stopped", "drone_id": str}` | Принудительная остановка зарядки |
| `GET_PORT_STATUS` | `{"filter": "all"\|"landed"\|"charging"}` | `{"drones": [...], "total": int, "timestamp": float}` | Получение списка дронов с диагностикой |

#### Формат ответа `GET_PORT_STATUS`

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
---
### Компоненты

#### DroneportOrchestrator
| Параметр | Значение |
|----------|----------|
| **Роль** | Маршрутизатор запросов от Эксплуатанта |
| **Вход** | `fleet_report`, `health_check` |
| **Выход** | Запросы к `DroneRegistry`, публикация в SITL |
| **Знает о** | Только DroneRegistry |
| **Не знает о** | PortManager, ChargingManager, DroneManager |

```python
# Пример: обработка запроса отчёта
def _handle_fleet_report(self, message):
    # Запрашивает агрегированные данные у Facade
    response = self.bus.request(
        registry_topics.GET_AGGREGATED_FLEET_STATUS,
        {"request_id": message["request_id"]}
    )
    return {"payload": response["payload"]}
```


#### DroneRegistry
| Параметр | Значение |
|----------|----------|
| **Роль** | Единый интерфейс ко всем данным дронопорта |
| **Вход** | `get_aggregated_status`, `register_drone`, `list_drones`, ... |
| **Выход** | Запросы к другим компонентам, события в брокер |
| **Знает о** | PortManager, ChargingManager, DroneManager, StateStore |
| **Хранит** | Ссылки на StateStore (Redis) |

```python
# Пример: агрегация статуса флота
def _handle_get_aggregated_status(self, message):
    drones = self.state.list_drones()           # из Redis
    ports = self.bus.request(port_topics.GET_PORT_STATUS)   # из PortManager
    charging = self.bus.request(charging_topics.GET_CHARGING_STATUS)  # из ChargingManager
    
    return {
        "fleet": {"total": len(drones), "charging": ..., "ready": ...},
        "ports": {"occupied": ..., "free": ...},
        "alerts": [...]
    }
```


#### DroneManager
| Параметр | Значение |
|----------|----------|
| **Роль** | Взаимодействие с физическими дронами (БВС) |
| **Вход** | `request_landing`, `request_takeoff`, `self_diagnostics` |
| **Выход** | `landing_allowed`, `takeoff_allowed`, события в Registry |
| **Знает о** | PortManager (через Broker), DroneRegistry (через Broker) |
| **Локально** | Кэш позиций дронов для SITL |

```python
# Пример: обработка запроса на посадку
def _handle_request_landing(self, message):
    drone_id = message["payload"]["drone_id"]
    
    # Запрашивает слот у PortManager
    response = self.bus.request(port_topics.REQUEST_LANDING_SLOT, ...)
    
    if response["status"] == "slot_assigned":
        # Публикует разрешение дрону
        self.bus.publish(topics.LANDING_ALLOWED, {"port_id": response["port_id"]})
        return {"status": "landing_allowed"}
```


#### PortManager
| Параметр | Значение |
|----------|----------|
| **Роль** | Управление посадочными площадками (слотами) |
| **Вход** | `reserve_slot`, `release_slot`, `request_landing_slot` |
| **Выход** | `slot_assigned`, `slot_released` |
| **Знает о** | StateStore (прямой доступ) |
| **Логика** | Проверка занятости, генерация коридора посадки |

```python
# Пример: поиск свободного слота
def _handle_request_landing_slot(self, message):
    for port_id in ["P-01", "P-02", "P-03", "P-04"]:
        if not self.state.is_port_occupied(port_id):
            return {
                "status": "slot_assigned",
                "port_id": port_id,
                "corridor": self._generate_landing_corridor(port_id)
            }
    return {"status": "denied", "reason": "No available slots"}
```


#### ChargingManager
| Параметр | Значение |
|----------|----------|
| **Роль** | Управление процессом зарядки дронов |
| **Вход** | `start_charging` (publish-only!), `stop_charging`, `charge_to_threshold` |
| **Выход** | `charging_started`, `charging_completed` (события) |
| **Знает о** | DroneRegistry (через Broker), StateStore (опционально) |
| **Особенность** | `start_charging` — **fire-and-forget**, без ответа |

```python
# Пример: publish-only команда
def _handle_start_charging(self, message):
    drone_id = message["payload"]["drone_id"]
    # Обновляет статус (через Registry или локально)
    self.bus.publish(
        topics.CHARGING_STARTED,
        {"drone_id": drone_id}
    )
    # ❌ Не возвращает ответ!
```

#### StateStore
| Параметр | Значение |
|----------|----------|
| **Роль** | Абстракция над Redis для хранения состояния |
| **Не наследуется** | От BaseComponent — не подключается к брокеру |
| **Методы** | `save_drone()`, `get_drone()`, `list_drones()`, `save_port()`, ... |
| **Используют** | DroneRegistry, PortManager, (опционально) ChargingManager |

```python
# Пример: сохранение дрона
def save_drone(self, drone_id: str, data: Dict[str, Any]) -> bool:
    key = f"drone:{drone_id}"
    return self.redis.hset(key, mapping=data) > 0
```

---


## Наземная управляющая станция
### Обзор системы

Наземная управляющая станция решает задачу централизованного управления группой дронов. Внешняя система (Эксплуатант) ставит задачи на выполнение миссий. Станция преобразует их в формат, понятный дронам (WPL), при необходимости разбивает на подмиссии для группы, загружает их на конкретные борта, контролирует выполнение и принимает подписанную телеметрию.

Система спроектирована с учётом требований безопасности: критически важные компоненты изолированы, а целостность данных обеспечивается цифровыми подписями.

---

### Архитектура

Архитектура описана с использованием методологии [C4 model](https://c4model.com/) и представлена в виде диаграмм PlantUML (папка `systems/gcs/docs/c4/`).

#### Контекст системы

*   **Эксплуатант** – внешняя система, которая отправляет команды `task.submit`, `task.assign`, `task.start`.
*   **НУС (GCS)** – ядро системы, преобразующее задачи в полётные задания и управляющее дронами.
*   **Дроны** – исполнители, принимают миссии в формате WPL и отправляют подписанную телеметрию.

Команды от эксплуатанта (topic: "v1.gcs.1.orchestrator"):

| Команды | Входные данные | Пример с необходимым содержимым | Выходные данные | Выход с ошибкой |
|---------|----------------|-----------------|---|---|
| task.submit | message: Dict[str, Any] | {"payload": {"start_point": {"lat":Any, "lon":Any, "alt":Any}, "end_point": {"lat":Any, "lon":Any, "alt":Any}}, "correlation_id": Any} | {"from": str, "mission_id": mission_id, "waypoints": list[{"lat":float, "lon":float, "alt":float}], "signature": signature} | {"from": str, "error": "failed to build route"} |
| task.assign | message: Dict[str, Any] | {"payload": {"mission_id":Any, "drone_id":Any}, "correlation_id": Any} | None | None |
| task.start | message: Dict[str, Any] | {"payload": {"mission_id":Any, "drone_id":Any}, "correlation_id": Any} | None | None |

Команды дрону (topic: "drone", входные данные: {"action": str, "sender": str, "payload": dict, "correlation_id": str}):
| action | sender | payload | correlation_id |
|---------|---------|-------|----|
|"drone.upload_mission"| "gcs_drone_manager" |{"mission_id": Any, "mission": str}| str |
|"drone.mission.start"| "gcs_drone_manager" | {} | str |

Формат "mission" в команде "upload_mission": 
```
        lines = ["QGC WPL 110"]
        for idx, point in enumerate(points):
            lat = point.get("lat", point.get("latitude", 0.0))
            lon = point.get("lon", point.get("lng", point.get("longitude", 0.0)))
            alt = point.get("alt", point.get("altitude", 0.0))
            params = point.get("params", {})

            line = "\t".join(
                [
                    str(idx),
                    "1" if idx == 0 else "0",
                    str(point.get("frame", 3)),
                    str(point.get("command", 16)),
                    str(params.get("p1", 0)),
                    str(params.get("p2", 0)),
                    str(params.get("p3", 0)),
                    str(params.get("p4", 0)),
                    str(lat),
                    str(lon),
                    str(alt),
                    "1",
                ]
            )
            lines.append(line)

        return "\n".join(lines)
```

#### Контейнеры

Система состоит из шести компонент, каждая из которых отвечает за выполнение определенной функции. Все сервисы общаются асинхронно через брокер сообщений (Kafka / MQTT), а состояние хранят в Redis.

| Контейнер           | Назначение                                                                 |
|---------------------|----------------------------------------------------------------------------|
| **DroneManager**    | Загружает подмиссии на конкретные дроны и даёт команду на старт.           |
| **DroneStore**      | Предоставляет доступ к данным дронов.                                      |
| **MissionConverter**  | Преобразует маршрут в формат WPL и подписывает миссию.                   |
| **MissionStore**    | Предоставляет доступ к данным миссий.                                      |
| **Orchestrator**    | Координирует выполнение задач от эксплуатанта: вызывает нужные менеджеры.  |
| **PathPlanner**     | Строит маршрут, соединяющий точку отправления и точку прибытия.            |

#### Уровни доверия

Анализ безопасности проведен в файле [GCS_SECURITY_ANALYSIS.md](./docs/GCS_SECURITY_ANALYSIS.md)

---

### Ключевые компоненты

#### DroneManager
*   На вход получает миссию.
*   Загружает её на конкретный дрон, обновляет данные миссии через `MissionStore` и статус дрона через `DroneStore`.
*   Подаёт команду на старт, обновляет данные миссии через `MissionStore` и статус дрона через `DroneStore`.

#### DroneStore
*   Имея доступ к Redis, предоставляет возможность получать и манипулировать данными дронов.

#### MissionConverter
*   Получает маршрут (список точек).
*   Конвертирует его в формат WPL (стандарт для дронов).
*   Вычисляет и добавляет цифровую подпись к миссии.
*   Сохраняет подписанную миссию через `MissionStore`.

#### MissionStore
*   Имея доступ к Redis, предоставляет возможность получать и манипулировать данными миссий.

#### Orchestrator
*   Принимает команды от эксплуатанта через брокер.
    *   "task.submit": вызывает `PathPlanner` для построения маршрута.
    *   "task.assign": последовательно вызывает `MissionConverter` для подготовления миссии, `DroneManager` для загрузки миссии.
    *   "task.start": вызывает `DroneManager` для старта миссии.

#### PathPlanner
*   Получает стартовую и финишную точки и формирует маршрут (список точек).


## Быстрый старт

### Предварительные требования

*   Установленный [Docker Desktop](https://docs.docker.com/get-docker/)
*   Python 3.13

### Настройка окружения

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/Kaitrye/DronePortGCS.git
   cd DronePortGCS
   ```
   **Важно:** все shell-скрипты (`.sh`) должны иметь окончания строк в формате **LF (Unix)**. Если вы работаете в Windows, выполните 
   ```
   dos2unix docker/kafka/entrypoint.sh docker/mqtt/entrypoint.sh
   ```
   после клонирования.
2. Создайте файл .env в папке docker/, например:
   ```
   cp docker/example.env docker/.env
   ```
   Отредактируйте переменные под ваши нужды (учётные записи пользователей, порты).

3. Установите зависимости:
   ```
   make init
   ```

### Запуск инфраструктуры
Запустите брокер сообщений (Kafka или MQTT) и Redis (если требуется). Управление осуществляется через Makefile из корня проекта.
- Запуск с брокером Kafka (по умолчанию):
  ```
  make docker-up
  ```
  или явно:
  ```
  make docker-up BROKER_TYPE=kafka
  ```
- Запуск с MQTT:
  ```
  make docker-up BROKER_TYPE=mqtt
  ```
  Проверить статус контейнеров можно командой:
  ```
  make docker-ps
  ```
  Просмотр логов:
  ```
  make docker-logs
  ```

### Выполнение тестов
- Модульные тесты:
  ```
  make unit-test
  ```
- Интеграционные тесты (запускают инфраструктуру и демо-системы автоматически):
  ```
  make integration-test
  ```
- Все тесты:
  ```
  make tests
  ```

## Общение между компонентами
### Типы взаимодействия

| Тип | Описание | Пример |
|-----|----------|--------|
| **Request/Response** | Запрос → ожидание ответа → обработка | Orchestrator → Registry: `get_aggregated_status` |
| **Publish-only** | Отправил и забыл (без ответа) | Orchestrator → ChargingManager: `start_charging` |
| **Event** | Публикация события для подписчиков | ChargingManager → все: `charging_started` |

### Формат сообщения

```json
{
  "action": "имя_действия",
  "payload": { ... },
  "correlation_id": "uuid-для-ответа",  // опционально, для request
  "reply_to": "топик_для_ответа"         // опционально, для request
}
```

## Структура репозитория
```
DronePortGCS/
├── .github/workflows/              # CI/CD (GitHub Actions)
├── broker/                         # Клиенты для работы с брокерами (Kafka, MQTT)
├── components/            
├── config/                         # Общие конфигурационные файлы (requirements.txt, pyproject.toml)               
├── docker/                         # Docker-файлы и конфигурации инфраструктуры
│   ├── kafka/                      # Скрипты и настройки для Kafka
│   ├── mqtt/                       # Скрипты и настройки для Mosquitto
│   ├── docker-compose.yml          # Docker Compose для брокеров и общих сервисов
│   └── .env                        # Файл переменных окружения
├── docs/                           # Документация и диаграммы          
├── sdk/                            # Внутренний SDK для разработки компонентов
├── systems/                        # Основные подсистемы GCS
│   ├── drone_port                  # Дронопорт
│   │   ├── docs/                   # Диаграммы и дополнительная документация
│   │   ├── src/
│   │   │   ├── charging_manager/       # Компонент ChargingManager
│   │   │   ├── drone_manager/          # Компонент DroneManager
│   │   │   ├── drone_registry/         # Компонент DroneRegistry
│   │   │   ├── droneport_orchestrator/ # Компонент DroneportOrchestrator
│   │   │   ├── port_manager/           # Компонент PortManager
│   │   │   └── state_store/            # Компонент StateStore
│   │   ├── tests/                  # Тесты для дронопорта
│   │   ├── docker-compose.yml      # Docker Compose для дронопорта
│   │   └── Makefile
│   ├── dummy_system/               # Тестовая система
│   └── gcs/                        # НУС
│       ├── docs/c4/                # Диаграммы
│       ├── src/
│       │   ├── drone_manager/          # Компонент для взаимодействия с дронами
│       │   ├── drone_store/            # Компонент для взаимодействия с базой данных дронов
│       │   ├── mission_converter/      # Компонент для подготовки миссий
│       │   ├── mission_store/          # Компонент для взаимодействия с базой данных миссий
│       │   ├── orchestrator/           # Оркестратор (главный координатор)
│       │   ├── path_planner/           # Компонент построения маршрута
│       │   ├── contracts.py            # Контракты доменной модели для GCS
│       │   ├── topic_naming.py         # Утилиты для именования топиков GCS
│       │   └── topics.py               # Общие топики и actions системы GCS
│       ├── tests/                  # Тесты для GCS
│       ├── docker-compose.yml      # Docker Compose для GCS
│       └── Makefile
├── tests/                          # Модульные и интеграционные тесты
├── Makefile                        # Автоматизация команд
└── LICENSE                         # Лицензия
```

## Технологический стек

*   **Язык:** Python 3.13
*   **Брокеры:** Apache Kafka, Eclipse Mosquitto (MQTT)
*   **Хранилище состояний:** Redis
*   **Контейнеризация:** Docker, Docker Compose
*   **Автоматизация:** Make
*   **Документирование:** PlantUML (C4-диаграммы)