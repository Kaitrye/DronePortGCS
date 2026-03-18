.PHONY: help init unit-test integration-test integration-test-run tests docker-up docker-down docker-logs docker-ps docker-clean dummy-system-up dummy-system-down gcs-system-up gcs-system-down

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml
DUMMY_COMPOSE = docker compose -f systems/dummy_system/.generated/docker-compose.yml --env-file systems/dummy_system/.generated/.env
GCS_COMPOSE = docker compose -f systems/gcs/.generated/docker-compose.yml --env-file systems/gcs/.generated/.env

help:
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make unit-test         - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make integration-test  - Интеграционные тесты (общие + dummy_system + gcs, docker required)"
	@echo "make integration-test-run - Только запуск integration pytest без lifecycle docker"
	@echo "make tests             - Все тесты"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		systems/dummy_system/tests/test_dummy_unit.py \
		systems/gcs/tests/unit/ \
		-v

integration-test: docker-up dummy-system-up gcs-system-up
	@$(MAKE) integration-test-run
	-$(MAKE) gcs-system-down
	-$(MAKE) dummy-system-down
	-$(MAKE) docker-down

integration-test-run:
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/integration/ \
		systems/dummy_system/tests/test_integration.py \
		systems/gcs/tests/integration/test_gcs_integration.py \
		-v

dummy-system-up: 
	@$(MAKE) -C systems/dummy_system prepare
	@set -a && . systems/dummy_system/.generated/.env && set +a && \
		$(DUMMY_COMPOSE) --profile $${BROKER_TYPE:-kafka} up -d --build --no-deps \
		dummy_component_a dummy_component_b

dummy-system-down:
	-@set -a && . systems/dummy_system/.generated/.env && set +a && \
		$(DUMMY_COMPOSE) rm -sf dummy_component_a dummy_component_b 2>/dev/null

gcs-system-up: 
	@$(MAKE) -C systems/gcs prepare
	@set -a && . systems/gcs/.generated/.env && set +a && \
		$(GCS_COMPOSE) --profile $${BROKER_TYPE:-kafka} up -d --build --no-deps \
		redis mission_store drone_store mission_converter orchestrator path_planner drone_manager

gcs-system-down:
	-@set -a && . systems/gcs/.generated/.env && set +a && \
		$(GCS_COMPOSE) rm -sf redis mission_store drone_store mission_converter orchestrator path_planner drone_manager 2>/dev/null

tests: unit-test integration-test

docker-up:
	@test -f docker/.env || cp docker/example.env docker/.env
	@$(LOAD_ENV) && profile="--profile $${BROKER_TYPE:-kafka}"; \
	$(DOCKER_COMPOSE) $$profile up -d

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down 2>/dev/null

docker-logs:
	$(DOCKER_COMPOSE) --profile $$(grep BROKER_TYPE docker/.env | cut -d= -f2) logs -f
	
docker-ps:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-clean:
	-$(DOCKER_COMPOSE) --profile kafka down -v --rmi local 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down -v --rmi local 2>/dev/null