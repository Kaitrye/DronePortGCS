FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY src/droneport_orchestrator/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЕ компоненты (оркестратор зависит от них)
COPY src/ /app/src/

# Копируем shared компоненты (если есть)
COPY shared/ /app/shared/ 2>/dev/null || true
COPY broker/ /app/broker/ 2>/dev/null || true

# Устанавливаем PYTHONPATH
ENV PYTHONPATH=/app

# Точка входа — оркестратор
CMD ["python", "-m", "src.droneport_orchestrator.src.orchestrator"]