.PHONY: help prepare unit-test integration-test tests docker-up docker-up-no-broker docker-down docker-down-no-broker docker-logs

PIPENV_PIPFILE = ../../config/Pipfile
PYTEST_CONFIG = ../../config/pyproject.toml
GENERATED = .generated
DOCKER_COMPOSE = docker compose -f $(GENERATED)/docker-compose.yml --env-file $(GENERATED)/.env

help:
	@echo "make prepare           - Собрать docker-compose + .env из компонентов"
	@echo "make docker-up         - Запустить систему (prepare + docker compose up)"
	@echo "make docker-up-no-broker - Запустить только сервисы GCS без брокера"
	@echo "make docker-down       - Остановить систему"
	@echo "make docker-down-no-broker - Остановить только сервисы GCS без брокера"
	@echo "make docker-logs       - Логи"
	@echo "make unit-test         - Проверка импортов/синтаксиса компонентов GCS"
	@echo "make integration-test  - Smoke интеграция (подъём GCS-стека)"
	@echo "make tests             - Все тесты"

prepare:
	@cd ../.. && PIPENV_PIPFILE=config/Pipfile pipenv run python scripts/prepare_system.py systems/gcs

docker-up: prepare
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} up -d --build

docker-up-no-broker: prepare
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} up -d --build --no-deps \
		redis mission_store drone_store mission_converter orchestrator path_planner drone_manager

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down 2>/dev/null

docker-down-no-broker:
	-@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) rm -sf mission_store drone_store mission_converter orchestrator path_planner drone_manager redis 2>/dev/null

docker-logs:
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} logs -f

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run python -m compileall components src -q

integration-test: docker-up
	@echo "Waiting for broker and gcs components..."
	@sleep 30
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} ps
	-$(MAKE) docker-down

tests: unit-test integration-test
