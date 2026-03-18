# Архитектура и методы Дронопорта (Droneport)

## Общая архитектура

Дронопорт построен на **микросервисной архитектуре** с использованием **событийно-ориентированного подхода**. Каждый компонент отвечает за строго определенную функцию и взаимодействует с другими через **SystemBus**.

## Компоненты и их методы

### 1. DroneportOrchestrator
**Роль**: Единственная точка входа для Эксплуатанта. 

| Метод | Топик | Входные данные | Выходные данные | Описание |
|-------|-------|----------------|-----------------|----------|
| `fleet_report` | `v1.droneport.{id}.orchestrator.fleet_report` | `{}` | Агрегированный статус системы | Запрос полного отчета о состоянии флота |
| `start_charging` | `v1.droneport.{id}.orchestrator.start_charging` | `{"drone_id": "DR-001"}` | Статус запуска зарядки | Команда на запуск зарядки дрона |

### 2. DroneRegistry
**Роль**: Центральный реестр дронов и фасад для внутренних компонентов. 

| Метод | Топик | Входные данные | Выходные данные | Описание |
|-------|-------|----------------|-----------------|----------|
| `register_drone` | `v1.droneport.{id}.registry.register_drone` | `{"drone_id": "DR-001", "model": "QuadroX", "owner": "Alpha"}` | `{"status": "success"}` | Регистрация нового дрона в системе |
| `list_drones` | `v1.droneport.{id}.registry.list_drones` | `{}` | `{"drones": [...]}` | Список всех зарегистрированных дронов (только метаданные) |
| `get_aggregated_status` | `v1.droneport.{id}.registry.get_aggregated_status` | `{}` | Агрегированный статус от всех менеджеров | Полный отчет о состоянии системы |
| `start_charging` | `v1.droneport.{id}.registry.start_charging` | `{"drone_id": "DR-001"}` | Статус от ChargingManager | Перенаправляет команду в ChargingManager |

### 3. DroneManager
**Роль**: Взаимодействие с физическими дронами. Принимает запросы от дронов и перенаправляет их в соответствующие компоненты.

| Метод | Топик | Входные данные | Выходные данные | Описание |
|-------|-------|----------------|-----------------|----------|
| `request_landing` | `v1.droneport.{id}.drone_manager.request_landing` | `{"drone_id": "DR-001", "battery": 95}` | `{"status": "allowed", "port_id": "P-01"}` | Запрос на посадку от дрона |
| `request_takeoff` | `v1.droneport.{id}.drone_manager.request_takeoff` | `{"drone_id": "DR-001"}` | `{"status": "allowed"}` | Запрос на взлет от дрона |
| `request_charging` | `v1.droneport.{id}.drone_manager.request_charging` | `{"drone_id": "DR-001", "target_battery": 90}` | Статус от ChargingManager | Запрос на зарядку от дрона |
| `get_available_drones` | `v1.droneport.{id}.drone_manager.get_available_drones` | `{}` | `{"drones": [...]}` | Список дронов на земле, готовых к вылету |

**События (публикует)**:
| Событие | Топик | Данные | Описание |
|---------|-------|--------|----------|
| `landing_allowed` | `v1.droneport.{id}.drone_manager.events.landing_allowed` | `{"drone_id": "DR-001", "port_id": "P-01"}` | Разрешение на посадку |
| `takeoff_allowed` | `v1.droneport.{id}.drone_manager.events.takeoff_allowed` | `{"drone_id": "DR-001"}` | Разрешение на взлет |
| `charging_requested` | `v1.droneport.{id}.drone_manager.events.charging_requested` | `{"drone_id": "DR-001", "port_id": "P-01"}` | Запрос зарядки отправлен |

### 4. PortManager
**Роль**: Управление посадочными площадками. Следит за занятостью слотов.

| Метод | Топик | Входные данные | Выходные данные | Описание |
|-------|-------|----------------|-----------------|----------|
| `reserve_slot` | `v1.droneport.{id}.port_manager.reserve_slot` | `{"port_id": "P-01", "drone_id": "DR-001"}` | `{"status": "reserved"}` | Резервирование конкретного слота |
| `release_slot` | `v1.droneport.{id}.port_manager.release_slot` | `{"port_id": "P-01"}` или `{"drone_id": "DR-001"}` | `{"status": "released"}` | Освобождение слота |
| `request_landing_slot` | `v1.droneport.{id}.port_manager.request_landing_slot` | `{"drone_id": "DR-001"}` | `{"status": "slot_assigned", "port_id": "P-01"}` | Запрос свободного слота для посадки |
| `get_port_status` | `v1.droneport.{id}.port_manager.get_port_status` | `{}` | `{"ports": [...]}` | Статус всех посадочных площадок |

**События (публикует)**:
| Событие | Топик | Данные | Описание |
|---------|-------|--------|----------|
| `slot_assigned` | `v1.droneport.{id}.port_manager.events.slot_assigned` | `{"port_id": "P-01", "drone_id": "DR-001"}` | Слот назначен дрону |
| `slot_released` | `v1.droneport.{id}.port_manager.events.slot_released` | `{"port_id": "P-01"}` | Слот освобожден |

### 5. ChargingManager
**Роль**: Управление зарядкой дронов. 

| Метод | Топик | Входные данные | Выходные данные | Описание |
|-------|-------|----------------|-----------------|----------|
| `start_charging` | `v1.droneport.{id}.charging_manager.start_charging` | `{"drone_id": "DR-001"}` | `{"status": "started"}` | Запуск зарядки дрона |

**События (публикует)**:
| Событие | Топик | Данные | Описание |
|---------|-------|--------|----------|
| `charging_started` | `v1.droneport.{id}.charging_manager.events.charging_started` | `{"drone_id": "DR-001"}` | Зарядка началась |
| `charging_completed` | `v1.droneport.{id}.charging_manager.events.charging_completed` | `{"drone_id": "DR-001"}` | Зарядка завершена |

## Сценарии взаимодействия

### Сценарий 1: Посадка дрона
```
Дрон -> DroneManager.request_landing
    DroneManager -> PortManager.request_landing_slot
    PortManager -> (находит свободный слот)
    PortManager публикует slot_assigned
    DroneManager публикует landing_allowed
    DroneManager отвечает дрону: {"status": "allowed", "port_id": "P-01"}
```

### Сценарий 2: Запуск зарядки от Эксплуатанта
```
Operator -> Orchestrator.start_charging
    Orchestrator -> DroneRegistry.start_charging
        DroneRegistry -> ChargingManager.start_charging
            ChargingManager публикует charging_started
            ChargingManager отвечает: {"status": "started"}
        DroneRegistry отвечает Orchestrator
    Orchestrator отвечает Operator
```

### Сценарий 3: Запрос полного отчета
```
Operator -> Orchestrator.fleet_report
    Orchestrator -> DroneRegistry.get_aggregated_status
        DroneRegistry -> DroneManager.get_available_drones
        DroneRegistry -> ChargingManager.get_charging_status
        DroneRegistry агрегирует данные
        DroneRegistry отвечает Orchestrator
    Orchestrator отвечает Operator
```

## Принципы архитектуры

1. **Единственная ответственность** - каждый компонент решает только свою задачу
2. **Минимум методов** - не более 3-4 методов на компонент
3. **Слабая связанность** - компоненты общаются только через SystemBus
4. **Фасад** - DroneRegistry как единая точка входа для внутренних запросов
5. **Событийность** - изменения состояния публикуются как события
6. **Stateless где возможно** - компоненты не хранят состояние, если это не необходимо

## Форматы сообщений

### Базовый формат запроса
```json
{
  "action": "method_name",
  "request_id": "uuid-1234",
  "timestamp": "2026-03-18T12:00:00Z",
  "payload": {
    // данные метода
  }
}
```

### Базовый формат ответа
```json
{
  "status": "success|error",
  "request_id": "uuid-1234",
  "timestamp": "2026-03-18T12:00:01Z",
  "payload": {
    // данные ответа
  }
}
```

### Базовый формат события
```json
{
  "event": "event_name",
  "timestamp": "2026-03-18T12:00:00Z",
  // специфичные для события поля
}
```