FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV COMPONENT_ID=drone_port_security_monitor
ENV PYTHONUNBUFFERED=1

EXPOSE 8081

CMD ["python", "-m", "systems.drone_port.src.security_monitor"]
