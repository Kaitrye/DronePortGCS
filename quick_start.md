<<<<<<< HEAD
# Docker

Развертывание брокеров и DummySystem в Docker.

## Быстрый старт (необходимо наличие docker и pipenv в системе)

```bash
cp docker/example.env docker/.env #(BROKER_TYPE=mqtt/kafka)
make docker-build
make docker-up
make docker-ps
```

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│                 Docker Network: drones_net           │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐                    │
│  │    Kafka    │  │  Mosquitto  │  (профиль kafka    │
│  │   :9092     │  │   :1883     │   или mqtt)        │
│  └─────────────┘  └─────────────┘                    │
│         │                  │                         │
│         └────────┬─────────┘                         │
│                  │                                   │
│  ┌───────────────┴───────────────┐                   │
│  │                               │                   │
│  │  dummy_system_a   dummy_system_b                  │
│  │      :9700             :9701                      │
│  │  (SystemBus: systems.dummy)                       │
│  └───────────────────────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| kafka | 9092 | Брокер сообщений (профиль kafka) |
| mosquitto | 1883 | MQTT брокер (профиль mqtt) |
| dummy_system_a | 9700 | DummySystem (echo, process) |
| dummy_system_b | 9701 | DummySystem |

## Команды

```bash
make docker-build   # Собрать образы
make docker-up      # Запустить (BROKER_TYPE=kafka или mqtt)
make docker-down    # Остановить
make docker-logs    # Логи
make docker-ps      # Статус
make docker-clean   # Остановить + удалить образы
```

## Конфигурация (.env)

```bash
cp docker/example.env docker/.env
```

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| BROKER_TYPE | kafka или mqtt | kafka |
| KAFKA_PORT | Порт Kafka | 9092 |
| MQTT_PORT | Порт MQTT | 1883 |
| DUMMY_PORT_A | Health порт dummy_system_a | 9700 |
| DUMMY_PORT_B | Health порт dummy_system_b | 9701 |
| DUMMY_USER_A | SASL/MQTT пользователь dummy_system_a | dummy_a |
| DUMMY_PASSWORD_A | | |
| DUMMY_USER_B | SASL/MQTT пользователь dummy_system_b | dummy_b |
| DUMMY_PASSWORD_B | | |
| ADMIN_USER | Для тестов (BROKER_USER) | admin |
| ADMIN_PASSWORD | | |

## Аутентификация

- **Kafka:** SASL PLAIN, JAAS (ADMIN_USER, DUMMY_USER_A, DUMMY_USER_B)
- **MQTT:** allow_anonymous false, passwd + ACL (readwrite systems/#, replies/#, drones/#)

## Тесты

Интеграционные тесты ожидают запущенные контейнеры:

```bash
make tests #Все тесты

make unit-test #Интеграционные тесты

make e2e-test #Сквозные тесты

make integration-test #Интеграционные тесты
```

## Troubleshooting

**Контейнер не запускается:**
```bash
docker logs dummy_system_a
```

**Брокер недоступен:** убедитесь что Kafka или Mosquitto запущен (profile kafka/mqtt).

**Сервисы не видят друг друга:** внутри Docker используйте имена контейнеров (kafka, mosquitto), а не localhost.
=======
# Quick Start

Брокер (Kafka/MQTT) + SDK. Шаблоны: `components/dummy_component`, `systems/dummy_system`.

## Структура

```
broker/              Шина, create_system_bus
sdk/                 BaseComponent, BaseSystem
components/          Standalone-компоненты
systems/             Системы (dummy_system)
docker/              Брокер (kafka, mosquitto)
scripts/             prepare_system.py
config/              Pipfile, pyproject.toml
```

## Команды

### Быстрый запуск (2 команды)

```bash
make init
make tests
```

### Корневой Makefile

```bash
make help              # Показать доступные команды
make init              # Установить pipenv и зависимости
make unit-test         # Unit тесты (SDK + broker + standalone компоненты)
make integration-test  # Интеграционные тесты (общие + dummy_system, нужен Docker)
make tests             # Все тесты

make docker-up         # Запустить инфраструктуру брокера
make docker-down       # Остановить инфраструктуру
make docker-logs       # Логи инфраструктуры
make docker-ps         # Статус контейнеров
make docker-clean      # Полная очистка docker ресурсов

make dummy-system-up   # Поднять systems/dummy_system
make dummy-system-down # Остановить systems/dummy_system
```

### Система: DummySystem

```bash
cd systems/dummy_system
make help              # Показать команды системы
make prepare           # Собрать .generated/docker-compose.yml + .env
make docker-up         # Поднять стек системы
make docker-down       # Остановить стек
make docker-logs       # Логи
make unit-test         # Unit тесты компонентов
make integration-test  # Интеграционные тесты (поднимает docker-up)
make tests             # Все тесты системы
```

### Система: GCS

```bash
cd systems/gcs
make help              # Показать команды системы
make prepare           # Собрать .generated/docker-compose.yml + .env
make docker-up         # Поднять стек системы
make docker-down       # Остановить стек
make docker-logs       # Логи
make unit-test         # Проверка синтаксиса/импортов компонентов
make integration-test  # Smoke-проверка поднятого стека
make tests             # Все проверки системы
```

## Протокол

Сообщения — dict: `action`, `payload`, `sender`, `correlation_id`, `reply_to`.

## Свой компонент/система

- **Компонент:** `components/README.MD`
- **Система:** `systems/README.md`

## Docker

```bash
cp docker/example.env docker/.env
# BROKER_TYPE=kafka или mqtt
make docker-up
```

| Переменная | Описание |
|------------|----------|
| BROKER_TYPE | kafka / mqtt |
| ADMIN_USER, ADMIN_PASSWORD | Админ брокера |
| COMPONENT_USER_A/B | Опционально, для компонентов |

## Troubleshooting

- Брокер недоступен: проверьте profile (kafka/mqtt) в docker-up
- Внутри Docker: имена контейнеров (kafka, mosquitto), не localhost
>>>>>>> origin/draft_GCS
