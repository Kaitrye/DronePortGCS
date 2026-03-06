.PHONY: help init unit-test integration-test tests docker-up docker-down docker-logs docker-ps docker-clean dummy-system-up dummy-system-down

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml

help:
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make unit-test         - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make integration-test  - Интеграционные тесты (общие + dummy_system, docker required)"
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
		-v

integration-test: docker-up dummy-system-up
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
