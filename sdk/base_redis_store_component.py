"""
BaseRedisStoreComponent — базовый класс для компонентов, использующих Redis.

Применяется в GCS MissionStore, DroneStore и похожих компонентах,
которым нужно постоянное key-value хранилище на базе Redis.
"""
from __future__ import annotations

import logging
import os
from abc import ABC
from typing import Optional

import redis

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent

logger = logging.getLogger(__name__)


class BaseRedisStoreComponent(BaseComponent, ABC):
    """
    BaseComponent со встроенным Redis-клиентом.

    Подклассам достаточно:
    1. Вызвать ``super().__init__(...)``, передав ``redis_db_env`` и ``redis_default_db``.
    2. Использовать ``self.redis_client`` для всех операций с Redis.

    Параметры подключения берутся из переменных окружения:
        REDIS_HOST      (по умолчанию: "redis")
        REDIS_PORT      (по умолчанию: 6379)
        <redis_db_env>  (по умолчанию: redis_default_db)
    """

    def __init__(
        self,
        component_id: str,
        component_type: str,
        topic: str,
        bus: SystemBus,
        redis_db_env: str = "REDIS_DB",
        redis_default_db: int = 0,
    ) -> None:
        redis_host = os.environ.get("REDIS_HOST", "redis")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_db = int(os.environ.get(redis_db_env, str(redis_default_db)))

        self.redis_client: redis.Redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

        try:
            self.redis_client.ping()
            logger.info(
                "[%s] Redis connected at %s:%s db=%s",
                component_id, redis_host, redis_port, redis_db,
            )
        except redis.ConnectionError as exc:
            logger.warning(
                "[%s] Redis not available at %s:%s db=%s — %s",
                component_id, redis_host, redis_port, redis_db, exc,
            )

        super().__init__(
            component_id=component_id,
            component_type=component_type,
            topic=topic,
            bus=bus,
        )
