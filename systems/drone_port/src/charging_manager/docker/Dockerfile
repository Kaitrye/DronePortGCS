FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY . .

ENV PYTHONPATH=/app
ENV COMPONENT_ID=charging_manager

EXPOSE 8084

CMD ["python", "-m", "src.charging_manager"]