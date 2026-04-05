# SITL Stub

Локальная заглушка SITL для ответа на `sitl.telemetry.request`.

Запуск:

```bash
python -m components.sitl_stub
```

Docker entrypoint:

```bash
docker build -f components/sitl_stub/docker/Dockerfile -t sitl-stub .
```
