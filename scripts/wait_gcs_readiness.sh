#!/usr/bin/env bash
set -euo pipefail

# Containers that must be started for GCS integration flow.
CONTAINERS=(
  "kafka"
  "drones-redis-1"
  "drones-orchestrator-1"
  "drones-mission_store-1"
  "drones-path_planner-1"
  "drones-drone_store-1"
  "drones-mission_converter-1"
  "drones-drone_manager-1"
)

# Kafka consumer groups that must be visible and assigned.
GROUPS=(
  "gcs_orchestrator_group_v1_gcs_1_orchestrator_v1"
  "gcs_mission_store_group_v1_gcs_1_mission_store_v1"
  "gcs_path_planner_group_v1_gcs_1_path_planner_v1"
  "gcs_drone_store_group_v1_gcs_1_drone_store_v1"
  "gcs_mission_converter_group_v1_gcs_1_mission_converter_v1"
  "gcs_drone_manager_group_v1_gcs_1_drone_manager_v1"
)

MAX_RETRIES="${MAX_RETRIES:-45}"
SLEEP_SEC="${SLEEP_SEC:-2}"
KAFKA_CONTAINER="${KAFKA_CONTAINER:-kafka}"
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"
KAFKA_CMD="${KAFKA_CMD:-/opt/kafka/bin/kafka-consumer-groups.sh}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

echo "[wait_gcs_readiness] Waiting for containers to be ready..."
for c in "${CONTAINERS[@]}"; do
  ready=0
  for ((i=1; i<=MAX_RETRIES; i++)); do
    state="$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "missing")"
    health="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null || echo "missing")"

    # Accept either healthy containers or containers without healthcheck but running.
    if [[ "$state" == "running" && ("$health" == "healthy" || "$health" == "none") ]]; then
      echo "[wait_gcs_readiness] Container $c is ready (state=$state, health=$health)"
      ready=1
      break
    fi

    echo "[wait_gcs_readiness] Waiting for $c (state=$state, health=$health)..."
    sleep "$SLEEP_SEC"
  done

  if [[ "$ready" -ne 1 ]]; then
    echo "[wait_gcs_readiness] ERROR: Container $c did not become ready"
    docker ps
    exit 1
  fi
done

echo "[wait_gcs_readiness] Waiting for Kafka consumer groups to stabilize..."

# Create SASL command config inside the kafka container (apache/kafka image uses SASL_PLAINTEXT)
docker exec "$KAFKA_CONTAINER" sh -c "printf 'security.protocol=SASL_PLAINTEXT\nsasl.mechanism=PLAIN\nsasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username=\"%s\" password=\"%s\";\n' '${ADMIN_USER}' '${ADMIN_PASSWORD}' > /tmp/gcs_readiness_admin.properties"

for g in "${GROUPS[@]}"; do
  ready=0
  for ((i=1; i<=MAX_RETRIES; i++)); do
    # $7 is CONSUMER-ID column; "-" means group exists but has no active members (dead group).
    members="$(docker exec "$KAFKA_CONTAINER" "$KAFKA_CMD" --bootstrap-server "$KAFKA_BOOTSTRAP" --command-config /tmp/gcs_readiness_admin.properties --describe --group "$g" 2>/dev/null | awk 'NR>1 && NF>0 && $7 != "-"')"

    if [[ -n "$members" ]]; then
      echo "[wait_gcs_readiness] Group $g is assigned"
      ready=1
      break
    fi

    echo "[wait_gcs_readiness] Waiting for group $g..."
    sleep "$SLEEP_SEC"
  done

  if [[ "$ready" -ne 1 ]]; then
    echo "[wait_gcs_readiness] ERROR: Group $g did not stabilize"
    docker logs "$KAFKA_CONTAINER" | tail -n 80
    exit 1
  fi
done

echo "[wait_gcs_readiness] All containers are ready and Kafka groups are stable."
echo "[wait_gcs_readiness] Sleeping 5s for extra stabilization..."
sleep 5
