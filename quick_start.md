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
