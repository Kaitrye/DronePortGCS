# systems/droneport/src/drone_registry/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/drone_registry/src/ ./src/

CMD ["python", "-c", "print('drone_registry component ready')"]