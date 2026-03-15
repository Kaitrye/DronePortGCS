.PHONY: help docker-up docker-down docker-build docker-rebuild logs test prepare health-check clean

# Variables
COMPOSE_FILE=docker-compose.yml
ENV_FILE=.env
PROJECT_NAME=droneport

help:
	@echo "Droneport Docker Commands:"
	@echo "  make docker-up        - Start all services"
	@echo "  make docker-down      - Stop all services"
	@echo "  make docker-build     - Build all containers"
	@echo "  make docker-rebuild   - Rebuild and restart"
	@echo "  make logs             - View all logs"
	@echo "  make logs-orch        - View orchestrator logs"
	@echo "  make logs-drone       - View drone_manager logs"
	@echo "  make logs-registry    - View drone_registry logs"
	@echo "  make logs-port        - View port_manager logs"
	@echo "  make logs-charging    - View charging_manager logs"
	@echo "  make logs-diagnostics - View diagnostics_manager logs"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make prepare          - Prepare environment"
	@echo "  make health-check     - Check service health"
	@echo "  make clean            - Clean up containers and volumes"

prepare:
	@echo "Preparing environment..."
	@if [ ! -f $(ENV_FILE) ]; then \
		cp example.env $(ENV_FILE); \
		echo "Created .env from example.env"; \
	fi
	@pip install -r requirements.txt
	@echo "Environment ready!"

docker-up:
	@echo "Starting Droneport services..."
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d
	@echo "Services started. Check status with: docker-compose ps"

docker-down:
	@echo "Stopping Droneport services..."
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down
	@echo "Services stopped"

docker-build:
	@echo "Building containers..."
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) build
	@echo "Build complete"

docker-rebuild: docker-down docker-build docker-up
	@echo "Rebuild complete"

logs:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

logs-orch:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f orchestrator

logs-drone:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f drone_manager

logs-registry:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f drone_registry

logs-port:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f port_manager

logs-charging:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f charging_manager

logs-diagnostics:
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f diagnostics_manager

test:
	@echo "Running all tests..."
	@pip install -r requirements.txt
	@pytest tests/ -v --cov=src --cov-report=html
	@echo "Tests complete. Coverage report in htmlcov/index.html"

test-unit:
	@echo "Running unit tests..."
	@pytest tests/unit -v --cov=src --cov-report=html

test-integration:
	@echo "Running integration tests..."
	@pytest tests/integration -v --cov=src --cov-report=html

health-check:
	@echo "Checking service health..."
	@curl -f http://localhost:8080/health || echo "Orchestrator: DOWN"
	@curl -f http://localhost:8081/health || echo "DroneManager: DOWN"
	@curl -f http://localhost:8082/health || echo "DroneRegistry: DOWN"
	@curl -f http://localhost:8083/health || echo "PortManager: DOWN"
	@curl -f http://localhost:8084/health || echo "ChargingManager: DOWN"
	@curl -f http://localhost:8085/health || echo "DiagnosticsManager: DOWN"

redis-cli:
	@docker exec -it droneport_redis redis-cli

clean:
	@echo "Cleaning up..."
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down -v
	@docker system prune -f
	@echo "Cleanup complete"

# SITL simulation profile
docker-up-sitl:
	@echo "Starting Droneport with SITL simulator..."
	@docker-compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) --env-file $(ENV_FILE) --profile simulation up -d
	@echo "SITL started on ports 5760/udp and 14550/udp"