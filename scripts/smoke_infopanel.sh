#!/usr/bin/env bash
# Sanity-check для локально поднятой Инфопанели (DroneAnalytics).
#
# Шлёт один тестовый safety_event на POST /api/log/event и печатает ответ.
# Используется ДО подъёма Дронопорт+НУС, чтобы отделить «Инфопанель не работает»
# от «наш InfopanelDispatcher не работает».
#
# Usage:
#   scripts/smoke_infopanel.sh <api-key> [url]
#
# Examples:
#   scripts/smoke_infopanel.sh change-me-api-key
#   scripts/smoke_infopanel.sh "$INFOPANEL_DRONE_PORT_API_KEY"
#   scripts/smoke_infopanel.sh my-key https://infopanel.example/api/log/event
#
# Ожидаемый успешный ответ (HTTP 200/207):
#   {"total":1,"accepted":1,"rejected":0,"errors":[]}

set -euo pipefail

KEY="${1:?usage: smoke_infopanel.sh <api-key> [url]}"
URL="${2:-https://localhost/api/log/event}"

TS_MS="$(date +%s%3N)"
PAYLOAD='[{
  "apiVersion": "1.1.0",
  "timestamp": '"${TS_MS}"',
  "event_type": "safety_event",
  "service": "dronePort",
  "service_id": 1,
  "severity": "warning",
  "message": "smoke test event from scripts/smoke_infopanel.sh"
}]'

echo "POST ${URL}"
echo "X-API-Key: ${KEY:0:8}... (${#KEY} chars)"
echo "Payload: ${PAYLOAD}"
echo "---"

# -k: принимаем self-signed cert (Инфопанель локально через make secrets).
# -w: выводим HTTP-код после тела ответа.
curl -k -sS -X POST "${URL}" \
  -H "X-API-Key: ${KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  -w '\nHTTP %{http_code}\n'
