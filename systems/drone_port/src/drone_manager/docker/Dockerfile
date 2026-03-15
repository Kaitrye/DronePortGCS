FROM python:3.11-slim

WORKDIR /app

# Копируем ВСЕ компоненты (оркестратор зависит от них)
COPY src/ /app/src/

RUN apt-get update

COPY . .

# Устанавливаем PYTHONPATH
ENV COMPONENT_ID=drone_manager
ENV PYTHONPATH=/app

EXPOSE 8081

CMD ["python", "-m", "src.drone_manager"]