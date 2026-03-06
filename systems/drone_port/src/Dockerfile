# systems/droneport/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всю структуру src/ (система + компоненты)
COPY src/ ./src/

# Точка входа: запуск droneport_system как приложения
CMD ["python", "-m", "src.droneport_system"]