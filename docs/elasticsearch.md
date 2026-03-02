# ELK — сбор логов приложения

Все сообщения через брокер (Kafka/MQTT) копируются в топик `logs.application` и пишутся в Elasticsearch.

## Включение

В `docker/.env`:
```
ENABLE_ELK=true
```

Перезапуск:
```bash
cd systems/dummy_system
make prepare
make docker-up
```

## Проверка логов

### 1. Kibana

Открыть http://localhost:5601

1. **Stack Management** → **Data** → **Index Patterns**
2. **Create index pattern** → `app-logs*` → Next → Create
3. **Analytics** → **Discover** → выбрать индекс `app-logs*`
4. В таблице: `direction` (in/out), `topic`, `message`, `timestamp`

### 2. Elasticsearch API

```bash
curl -s "http://localhost:9200/app-logs/_search?pretty&size=5"
```

Поля: `direction`, `topic`, `message` (оригинальное сообщение), `timestamp`.

### 3. Появились ли логи

После `make docker-up` подождать 1–2 минуты. Вызвать echo через тест или вручную — логи появятся через несколько секунд.

```bash
# Запустить интеграционный тест
cd systems/dummy_system && make integration-test
# Затем проверить Kibana или curl
```

## log-consumer: Elasticsearch unavailable

Если `docker logs log-consumer` показывает `Elasticsearch unavailable`:

1. **Elasticsearch запущен?**
   ```bash
   docker ps | grep elasticsearch
   docker logs elasticsearch
   ```
   Если контейнера нет — проверьте `ENABLE_ELK=true` в `.env` и `--profile elk` при `docker compose up`.

2. **Проверить доступ к Elasticsearch с хоста:**
   ```bash
   curl -s http://localhost:9200/_cluster/health
   ```

3. **log-consumer ждёт до 2 минут** и при ошибках логирует причину. После `restart: on-failure` перезапуск произойдёт автоматически.

4. **Полный рестарт стека:**
   ```bash
   cd systems/dummy_system && make docker-down && make docker-up
   ```

## Индекс не найден (index_not_found_exception)

Индекс создаётся при первой записи. Если `app-logs` отсутствует:

1. **ENABLE_ELK включён?**
   ```bash
   grep ENABLE_ELK systems/dummy_system/.generated/.env
   # Должно быть: ENABLE_ELK=true
   ```

2. **log-consumer запущен?**
   ```bash
   docker ps | grep log-consumer
   docker logs log-consumer
   ```
   Должно быть: `[log-consumer] Kafka: reading logs.application` или `MQTT: reading logs/application`, без ошибок.

3. **Нужен трафик.** Без сообщений между компонентами логи не появятся:
   ```bash
   cd systems/dummy_system && make integration-test
   ```

4. **Проверить индексы Elasticsearch:**
   ```bash
   curl -s "http://localhost:9200/_cat/indices?v"
   ```
