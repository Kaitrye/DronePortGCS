.PHONY: help prepare unit-test integration-test tests docker-up docker-down docker-logs

PIPENV_PIPFILE = ../../config/Pipfile
PYTEST_CONFIG = ../../config/pyproject.toml
GENERATED = .generated
DOCKER_COMPOSE = docker compose -f $(GENERATED)/docker-compose.yml --env-file $(GENERATED)/.env

help:
	@echo "make prepare           - Собрать docker-compose + .env из компонентов"
	@echo "make docker-up         - Запустить систему (prepare + docker compose up)"
	@echo "make docker-down       - Остановить систему"
	@echo "make docker-logs       - Логи всех компонентов"
	@echo "make unit-test         - Unit тесты компонентов"
	@echo "make integration-test  - Интеграционные тесты (docker required)"
	@echo "make tests             - Все тесты (unit + integration)"

prepare:
	@cd ../.. && PIPENV_PIPFILE=config/Pipfile pipenv run python scripts/prepare_system.py systems/drone_port

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
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) systems/drone_port/tests/unit/ -v

integration-test: docker-up
	@echo "Waiting for broker and components to be ready..."
	@sleep 45
	@set -a && . $(GENERATED)/.env && set +a && \
		PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) systems/drone_port/tests/test_integration.py -v
	-$(MAKE) docker-down

tests: unit-test integration-test