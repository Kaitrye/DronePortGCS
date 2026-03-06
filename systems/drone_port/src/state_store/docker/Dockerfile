# systems/droneport/src/state_store/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только src/ компонента (не весь systems/)
COPY src/state_store/src/ ./src/

# Запуск не требуется — это библиотека, но для совместимости с CI/CD:
CMD ["python", "-c", "print('state_store component ready')"]