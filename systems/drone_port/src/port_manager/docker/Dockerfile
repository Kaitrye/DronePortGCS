# systems/droneport/src/port_manager/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/port_manager/src/ ./src/

CMD ["python", "-c", "print('port_manager component ready')"]