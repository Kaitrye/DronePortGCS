.PHONY: help prepare init unit-test tests docker-up docker-down docker-logs docker-ps docker-clean

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml

help:
	@echo "make prepare           - Установить системные пакеты (apt: python3, pip, docker, docker-compose, pipenv)"
	@echo "make init              - Установить pipenv и Python-зависимости проекта"
	@echo "make unit-test         - Unit тесты (SDK + broker + компоненты)"
	@echo "make tests             - Все тесты"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"

prepare:
	@echo "Установка системных пакетов через apt..."
	@command -v apt-get >/dev/null 2>&1 || { echo "Ошибка: apt-get не найден. make prepare поддерживает только Debian/Ubuntu (apt)."; exit 1; }
	sudo apt-get update
	sudo apt-get install -y python3 python3-pip python3-venv docker.io docker-compose-v2
	pip3 install --user pipenv
	@echo "Готово. Следующий шаг: make init"

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		-v

tests: unit-test

docker-up:
	@test -f docker/.env || cp docker/example.env docker/.env
	@set -a && . docker/.env && set +a && \
		profiles="--profile $${BROKER_TYPE:-kafka}"; \
		[ "$${ENABLE_ELK:-false}" = "true" ] && profiles="$$profiles --profile elk"; \
		$(DOCKER_COMPOSE) $$profiles up -d

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka --profile elk down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt --profile elk down 2>/dev/null

docker-logs:
	$(DOCKER_COMPOSE) --profile $$(grep BROKER_TYPE docker/.env | cut -d= -f2) logs -f

docker-ps:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-clean:
	-$(DOCKER_COMPOSE) --profile kafka down -v --rmi local 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down -v --rmi local 2>/dev/null
