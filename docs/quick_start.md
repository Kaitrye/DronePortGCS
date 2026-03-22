# Quick Start

Быстрый старт по репозиторию `DronePortGCS`: общая инфраструктура, `GCS`, `DronePort`, тесты и основные команды.

## Что в репозитории

- `broker/` - шина сообщений и фабрика брокеров
- `sdk/` - базовые классы, протокол сообщений, общие утилиты
- `components/` - standalone-компоненты
- `systems/gcs/` - наземная станция управления миссиями
- `systems/drone_port/` - сервис дронопорта
- `docker/` - общая брокерная инфраструктура
- `docs/` - общая документация

## Требования

- Docker + Docker Compose
- Python `>= 3.12`
- `pipenv`

## Быстрый сценарий

```bash
cp docker/example.env docker/.env
make init
make docker-up
make gcs-system-up
make drone-port-system-up
```

Остановить всё:

```bash
make gcs-system-down
make drone-port-system-down
make docker-down
```

## Основные команды

```bash
make help
make init
make unit-test
make integration-test
make integration-test-run
make tests
```

```bash
make docker-up
make docker-down
make docker-logs
make docker-ps
make docker-clean
```

```bash
make gcs-system-up
make gcs-system-down
make drone-port-system-up
make drone-port-system-down
```

## Что делают system-up команды

`make gcs-system-up`:

- запускает `make -C systems/gcs prepare`
- генерирует `systems/gcs/.generated/docker-compose.yml`
- генерирует `systems/gcs/.generated/.env`
- поднимает `redis`, `mission_store`, `drone_store`, `mission_converter`, `orchestrator`, `path_planner`, `drone_manager`

`make drone-port-system-up`:

- запускает `make -C systems/drone_port prepare`
- генерирует `systems/drone_port/.generated/docker-compose.yml`
- генерирует `systems/drone_port/.generated/.env`
- поднимает `redis`, `state_store`, `port_manager`, `drone_registry`, `charging_manager`, `drone_manager`, `orchestrator`

Если нужен только prepare без запуска:

```bash
make -C systems/gcs prepare
make -C systems/drone_port prepare
```

## Брокер и env

Сейчас в документации и рабочем сценарии поддерживается только `MQTT`.

Основные переменные в `docker/.env`:

| Переменная | Назначение |
|------------|------------|
| `BROKER_TYPE` | Тип брокера. Используйте `mqtt` |
| `INSTANCE_ID` | Идентификатор экземпляра системы |
| `ADMIN_USER` | Логин администратора брокера |
| `ADMIN_PASSWORD` | Пароль администратора брокера |

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

Если docker-стек уже поднят вручную и нужен только pytest:

```bash
make integration-test-run
```

## Полезные ссылки

- [README.md](/home/kaitrye/DronePortGCS/README.md)
- [Makefile](/home/kaitrye/DronePortGCS/Makefile)
- [systems/gcs/docs/c4/README.md](/home/kaitrye/DronePortGCS/systems/gcs/docs/c4/README.md)
