# 🚁 DronePort: Описание архитектуры компонентов

## 📋 Оглавление

1. [Что такое DronePort?](#-что-такое-droneport)
2. [Архитектура в одном слайде](#-архитектура-в-одном-слайде)
3. [Компоненты системы](#-компоненты-системы)
4. [Как компоненты общаются](#-как-компоненты-общаются)
5. [Поток данных: пример сценария](#-поток-данных-пример-сценария)
6. [Ключевые концепции](#-ключевые-концепции)
7. [Быстрый старт](#-быстрый-старт)

---

## 🔍 Что такое DronePort?

**DronePort** — это система управления дронопортом (вертодронной площадкой), которая:

| Функция | Описание |
|---------|----------|
| 🛬 **Посадка** | Координация посадки дронов на свободные площадки |
| 🛫 **Взлёт** | Проверка готовности и разрешение на вылет |
| 🔋 **Зарядка** | Управление процессом зарядки аккумуляторов |
| 📊 **Мониторинг** | Агрегация статуса всех дронов для оператора |
| 🧪 **SITL** | Интеграция с симулятором для тестирования |

**Главный принцип**: каждый компонент делает **одну задачу** и общается с другими **только через брокер сообщений** (MQTT).

---

## 🏗 Архитектура в одном слайде

```
┌─────────────────────────────────────────────┐
│              ЭКСПЛУАТАНТ                     │
│         (оператор / внешняя система)         │
└────────────────┬────────────────────────────┘
                 │ запросы: fleet_report, health_check
                 ▼
┌─────────────────────────────────────────────┐
│         DRONEPORT ORCHESTRATOR              │
│  • Единственная точка входа от оператора    │
│  • НЕ знает о других компонентах напрямую   │
│  • Маршрутизирует запросы → DroneRegistry   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│            DRONE REGISTRY ⭐                │
│              (Facade-паттерн)               │
│  • Знает о ВСЕХ компонентах дронопорта     │
│  • Агрегирует данные из:                    │
│    - PortManager (слоты)                    │
│    - ChargingManager (зарядка)              │
│    - DroneManager (статус дронов)           │
│  • Хранит состояние в StateStore (Redis)    │
└───────┬────────────┬────────────┬───────────┘
        │            │            │
        ▼            ▼            ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│PortManager│ │ChargingMgr│ │DroneManager│
│• слоты    │ │• зарядка  │ │• дроны    │
│• посадка  │ │• батарея  │ │• телеметрия│
│• взлёт    │ │• мощность │ │• SITL     │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └──────┬──────┴──────┬──────┘
             ▼             ▼
    ┌─────────────────────────┐
    │      STATE STORE        │
    │   (Redis, пассивный)    │
    │ • drone:{id} → данные  │
    │ • port:{id} → статус   │
    └─────────────────────────┘
```

> ⭐ **DroneRegistry — это Facade**: Orchestrator общается **только** с ним, не зная о внутренней структуре дронопорта.

---

## 🧩 Компоненты системы

### 1️⃣ DroneportOrchestrator
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

---

### 2️⃣ DroneRegistry ⭐ (Facade)
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

---

### 3️⃣ DroneManager
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

---

### 4️⃣ PortManager
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

---

### 5️⃣ ChargingManager
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

---

### 6️⃣ StateStore (пассивный)
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

## 📡 Как компоненты общаются

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

### Топики (именование)

```
v1.droneport.{system_id}.{component}.{action}
```

Примеры:
- `v1.droneport.dp-001.orchestrator.fleet_report` — запрос отчёта
- `v1.droneport.dp-001.registry.get_aggregated_status` — Facade-запрос
- `v1.droneport.dp-001.charging_manager.events.charging_started` — событие

---

## 🔄 Поток данных: пример сценария

### 🛬 Посадка дрона

```
1. Дрон → DroneManager: request_landing {drone_id: "D-001"}
2. DroneManager → PortManager: request_landing_slot {drone_id: "D-001"}
3. PortManager → StateStore: проверка занятости слотов
4. PortManager → DroneManager: slot_assigned {port_id: "P-02"}
5. DroneManager → DroneRegistry: register_drone {drone_id: "D-001", port_id: "P-02"}
6. DroneManager → Дрон: landing_allowed {port_id: "P-02", corridor: {...}}
7. DroneRegistry → StateStore: сохранение статуса дрона
```

### 🔋 Запуск зарядки (publish-only)

```
1. Эксплуатант → Orchestrator: fleet_report
2. Orchestrator → DroneRegistry: get_aggregated_status
3. DroneRegistry → ChargingManager: get_charging_status
4. ChargingManager → StateStore: чтение статусов
5. ChargingManager → DroneRegistry: ответ со списком заряжающихся
6. ... (агрегация и возврат отчёта)

7. Параллельно: Эксплуатант → Orchestrator: start_charging {drone_id: "D-001"}
8. Orchestrator → ChargingManager: publish start_charging (без ожидания ответа!)
9. ChargingManager → StateStore: обновление статуса дрона
10. ChargingManager → все: событие charging_started
```

---

## 🎯 Ключевые концепции

### ✅ Facade-паттерн (DroneRegistry)
- Orchestrator **не знает** о внутренней структуре дронопорта
- Все запросы к данным идут **только** через DroneRegistry
- Упрощает тестирование и замену компонентов

### ✅ Publish-only команды
- Некоторые действия (например, `start_charging`) не требуют подтверждения
- Уменьшает задержки и упрощает протокол
- Ответственность за обработку ошибок — на стороне получателя

### ✅ Пассивный StateStore
- Не подключается к брокеру, не имеет handlers
- Прямой доступ к Redis через методы
- Используется только компонентами, которым нужно хранить состояние

### ✅ Изоляция компонентов
- Каждый компонент знает **минимум** о других
- Взаимодействие — только через Broker (MQTT)
- Легко заменять/масштабировать отдельные части

---

## 🚀 Быстрый старт

### 1. Запуск через Docker

```bash
# Из корня репозитория
cd DronePortGCS

# Запуск всех компонентов дронопорта
docker-compose -f systems/drone_port/docker-compose.yml up --build

# Или только отдельные компоненты
docker-compose -f systems/drone_port/docker-compose.yml up --build redis mqtt charging_manager
```

### 2. Проверка работы

```bash
# Логи компонента
docker-compose -f systems/drone_port/docker-compose.yml logs -f charging_manager

# Подписка на топики через MQTT
docker exec -it <mqtt_container> mosquitto_sub -v -t "v1.droneport.dp-001.#"

# Проверка Redis
docker exec -it <redis_container> redis-cli KEYS "drone:*"
```
