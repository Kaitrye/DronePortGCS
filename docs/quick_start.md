# Quick Start

Инфрраструктура для взаимодействия компонентов через брокер сообщений (Kafka / MQTT).
Каждый компонент подключается к общей шине (`SystemBus`), обменивается сообщениями по топикам
и обрабатывает входящие запросы через маршрутизацию по `action`.

## Структура проекта

```
broker/              Шина сообщений (SystemBus, create_system_bus)
sdk/                 Базовые классы (BaseComponent, BaseSystem)
components/          Отдельные компоненты (шаблон: dummy_component)
systems/             Системы из нескольких компонентов (шаблон: dummy_system)
docker/              Инфраструктура брокера (Kafka, Mosquitto, ELK)
scripts/             Скрипты сборки (prepare_system.py)
config/              Pipfile, pyproject.toml, requirements.txt
docs/                Документация
```

## 1. Установка окружения

### Требования

- Python 3.12+
- Docker + Docker Compose
- pipenv

### Установка системных пакетов (Debian/Ubuntu)

```bash
make prepare
```

Устанавливает через `apt`: `python3`, `pip`, `docker.io`, `docker-compose-v2`, `pipenv`.

> **Только для систем с `apt`** (Debian, Ubuntu и производные).
> На macOS, Arch и других дистрибутивах установите пакеты вручную.

### Инициализация проекта

```bash
make init
```

Устанавливает Python-зависимости из `config/Pipfile` (включая dev-пакеты) через `pipenv`.

## 2. Настройка Docker

Создайте файл конфигурации из шаблона:

```bash
cp docker/example.env docker/.env
```

Основные переменные в `docker/.env`:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BROKER_TYPE` | Тип брокера: `kafka` или `mqtt` | `kafka` |
| `ADMIN_USER` | Логин администратора брокера | `admin` |
| `ADMIN_PASSWORD` | Пароль администратора | `admin_secret_123` |
| `COMPONENT_USER_A/B` | Отдельные учётные данные для компонентов (опционально) | — |
| `DOCKER_NETWORK` | Имя Docker-сети | `drones_net` |
| `ENABLE_ELK` | Включить сбор логов в Elasticsearch | `false` |

## 3. Запуск инфраструктуры (только брокер)

```bash
make docker-up
```

Поднимает Kafka (или Mosquitto, в зависимости от `BROKER_TYPE`).
Если `ENABLE_ELK=true` — дополнительно поднимает Elasticsearch, Kibana и log-consumer.

Другие команды:

```bash
make docker-down     # Остановить все контейнеры
make docker-logs     # Следить за логами брокера
make docker-ps       # Статус контейнеров
make docker-clean    # Остановить + удалить volumes и образы
```

## 4. Запуск системы (брокер + компоненты)

Система объединяет несколько компонентов и инфраструктуру в единый docker-compose.

```bash
cd systems/dummy_system
make docker-up
```

Эта команда автоматически выполняет `make prepare` (генерация `.generated/docker-compose.yml`
и `.generated/.env`), а затем поднимает все контейнеры.

Команды системы:

```bash
make prepare           # Сгенерировать .generated/ без запуска
make docker-up         # prepare + запуск всех контейнеров (брокер + компоненты)
make docker-down       # Остановить систему
make docker-logs       # Логи всех сервисов
make unit-test         # Unit-тесты компонентов системы
make integration-test  # Интеграционные тесты (поднимает Docker, ждёт готовности, запускает тесты)
make tests             # unit-test + integration-test
```

## 5. Тестирование

Из корня проекта — тесты SDK и брокера:

```bash
make tests
```

Запускает unit-тесты из `tests/unit/` и `components/dummy_component/tests/`.

Из директории системы — тесты компонентов и интеграция:

```bash
cd systems/dummy_system
make unit-test          # Быстрые тесты без Docker
make integration-test   # Полный цикл: docker-up → ожидание → pytest → docker-down
```

## 6. Протокол сообщений

Все сообщения — `dict` со следующими полями:

| Поле | Тип | Описание |
|------|-----|----------|
| `action` | `str` | Действие для маршрутизации (обязательное) |
| `payload` | `dict` | Данные сообщения |
| `sender` | `str` | Идентификатор отправителя |
| `correlation_id` | `str` | Связь запроса и ответа (для request/response) |
| `reply_to` | `str` | Топик для ответа |

## 7. ELK (логирование)

При `ENABLE_ELK=true` все сообщения через брокер дублируются в топик `logs.application`,
откуда `log-consumer` пишет их в Elasticsearch. Просмотр — через Kibana (http://localhost:5601).

Подробнее: [docker/README_ELK.md](../docker/README_ELK.md)

## Создание своих компонентов и систем

- **Компонент:** [components/README.MD](../components/README.MD)
- **Система:** [systems/README.md](../systems/README.md)
- **Брокер и Docker:** [docker/README.md](../docker/README.md)
- **Конфигурация:** [config/README.md](../config/README.md)

## Troubleshooting

- **Брокер недоступен** — проверьте `BROKER_TYPE` в `docker/.env` и что `make docker-up` завершился без ошибок.
- **Внутри Docker** — используйте имена контейнеров (`kafka`, `mosquitto`), не `localhost`.
- **Elasticsearch не запускается** — см. [docker/README_ELK.md](../docker/README_ELK.md).
- **Тесты падают** — убедитесь, что `make init` выполнен и Docker запущен.
