FROM python:3.13-slim

WORKDIR /app

COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "components.orvd_stub"]
