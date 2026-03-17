.PHONY: help prepare unit-test integration-test integration-test-run tests docker-up docker-down docker-logs

PIPENV_PIPFILE = ../../config/Pipfile
PYTEST_CONFIG = ../../config/pyproject.toml
GENERATED = .generated
DOCKER_COMPOSE = docker compose -f $(GENERATED)/docker-compose.yml --env-file $(GENERATED)/.env

help:
	@echo "make prepare           - Собрать docker-compose + .env из компонентов"
	@echo "make docker-up         - Запустить систему (prepare + docker compose up)"
	@echo "make docker-down       - Остановить систему"
	@echo "make docker-logs       - Логи"
	@echo "make unit-test         - Unit тесты компонентов"
	@echo "make integration-test  - Интеграционные тесты (docker-up + run + docker-down)"
	@echo "make integration-test-run - Интеграционные тесты (только запуск pytest)"
	@echo "make tests             - Все тесты"

prepare:
	@cd ../.. && PIPENV_PIPFILE=config/Pipfile pipenv run python scripts/prepare_system.py systems/dummy_system

docker-up: prepare
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} up -d --build

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down 2>/dev/null

docker-logs:
	@set -a && . $(GENERATED)/.env && set +a && \
		$(DOCKER_COMPOSE) --profile $${BROKER_TYPE:-kafka} logs -f

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/test_dummy_unit.py -v

integration-test-run:
	@set -a && . $(GENERATED)/.env && set +a && \
		PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/test_integration.py -v

integration-test: docker-up 
	@echo "Waiting for broker and components..."
	@sleep 10
	-$(MAKE) integration-test-run
	-$(MAKE) docker-down

tests: unit-test integration-test
