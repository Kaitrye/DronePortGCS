<<<<<<< HEAD
.PHONY: help init install shell tests e2e-test unit-test integration-test dummy-component-integration-test docker-build docker-up docker-down docker-logs docker-ps docker-clean
=======
.PHONY: help init unit-test integration-test tests docker-up docker-down docker-logs docker-ps docker-clean dummy-system-up dummy-system-down
>>>>>>> origin/draft_GCS

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml

help:
<<<<<<< HEAD
	@echo "make init            - Установить pipenv и зависимости"
	@echo "make tests           - Docker up + pytest + docker-down"
	@echo "make e2e-test        - E2E тесты"
	@echo "make unit-test       - Unit тесты"
	@echo "make integration-test - Интеграционные тесты"
	@echo "make dummy-component-integration-test - Интеграционные тесты DummyComponent + брокер"
	@echo "make docker-build    - Собрать образы"
	@echo "make docker-up       - Запустить контейнеры"
	@echo "make docker-down     - Остановить"
	@echo "make docker-logs     - Логи"
	@echo "make docker-ps       - Статус"
	@echo "make docker-clean    - Очистка"
=======
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make unit-test         - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make integration-test  - Интеграционные тесты (общие + dummy_system, docker required)"
	@echo "make tests             - Все тесты"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"
>>>>>>> origin/draft_GCS

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

<<<<<<< HEAD
tests:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && export BROKER_TYPE MQTT_PORT KAFKA_PORT && $(MAKE) docker-up
	@sleep 20
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/ -v
	-$(MAKE) docker-down

e2e-test:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && export BROKER_TYPE MQTT_PORT KAFKA_PORT && $(MAKE) docker-up
	@sleep 20
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/e2e/ -v
	-$(MAKE) docker-down

unit-test:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && export BROKER_TYPE MQTT_PORT KAFKA_PORT && $(MAKE) docker-up
	@sleep 20
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/unit/ -v
	-$(MAKE) docker-down

integration-test:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && export BROKER_TYPE MQTT_PORT KAFKA_PORT && $(MAKE) docker-up
	@sleep 20
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/integration/ -v
	-$(MAKE) docker-down

dummy-component-integration-test:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && export BROKER_TYPE MQTT_PORT KAFKA_PORT && $(MAKE) docker-up
	@sleep 20
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) components/dummy_component/tests/integration/ -v
	-$(MAKE) docker-down

docker-build:
	@test -f docker/.env || cp docker/example.env docker/.env
	$(DOCKER_COMPOSE) --profile kafka build
	$(DOCKER_COMPOSE) --profile mqtt build
=======
unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		systems/dummy_system/tests/test_dummy_unit.py \
		-v

integration-test: dummy-system-up
	@echo "Waiting for broker and components..."
	@sleep 45
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/integration/ \
		systems/dummy_system/tests/test_integration.py \
		-v
	-$(MAKE) dummy-system-down

dummy-system-up:
	@$(MAKE) -C systems/dummy_system docker-up

dummy-system-down:
	-$(MAKE) -C systems/dummy_system docker-down

tests: unit-test integration-test
>>>>>>> origin/draft_GCS

docker-up:
	@test -f docker/.env || cp docker/example.env docker/.env
	@profile=$${BROKER_TYPE:-$$(grep '^BROKER_TYPE=' docker/.env 2>/dev/null | cut -d= -f2)}; \
	profile=$${profile:-kafka}; \
<<<<<<< HEAD
	$(DOCKER_COMPOSE) --profile $$profile up -d --build
=======
	$(DOCKER_COMPOSE) --profile $$profile up -d
>>>>>>> origin/draft_GCS

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down 2>/dev/null
<<<<<<< HEAD
	-docker ps -aq --filter "label=type=drone" | xargs -r docker rm -f
=======
>>>>>>> origin/draft_GCS

docker-logs:
	$(DOCKER_COMPOSE) --profile $$(grep BROKER_TYPE docker/.env | cut -d= -f2) logs -f

docker-ps:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-clean:
	-$(DOCKER_COMPOSE) --profile kafka down -v --rmi local 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down -v --rmi local 2>/dev/null
<<<<<<< HEAD
	-docker ps -aq --filter "label=type=drone" | xargs -r docker rm -f
	-docker images -q "drones_v2*" | xargs -r docker rmi -f
=======
>>>>>>> origin/draft_GCS
