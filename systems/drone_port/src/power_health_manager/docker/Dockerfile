# systems/droneport/src/power_health_manager/Dockerfile
FROM python3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/power_health_manager/src/ ./src/
COPY src/power_health_manager/tests/ ./tests/

# Для тестов (опционально, но полезно для CI)
CMD ["python", "-m", "pytest", "tests/"]