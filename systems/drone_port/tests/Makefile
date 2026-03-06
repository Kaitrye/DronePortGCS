.PHONY: build run test clean test-all coverage

build:
	docker-compose build

run:
	docker-compose up

test:
	docker-compose run --rm power_health_manager_test

test-all:
	docker-compose run --rm state_store_test
	docker-compose run --rm drone_registry_test
	docker-compose run --rm port_manager_test
	docker-compose run --rm power_health_manager_test
	docker-compose run --rm orchestrator_test

coverage:
	docker-compose run --rm state_store_test pytest --cov=src/state_store --cov-report=html
	docker-compose run --rm drone_registry_test pytest --cov=src/drone_registry --cov-report=html
	docker-compose run --rm port_manager_test pytest --cov=src/port_manager --cov-report=html
	docker-compose run --rm power_health_manager_test pytest --cov=src/power_health_manager --cov-report=html
	docker-compose run --rm orchestrator_test pytest --cov=src/droneport_orchestrator --cov-report=html

clean:
	docker-compose down
	rm -rf htmlcov/