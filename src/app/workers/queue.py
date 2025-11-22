"""Queue configuration for background tasks."""
from typing import Optional
import redis
from rq import Queue

from src.app.config import settings
from src.app.logging_config import get_logger

logger = get_logger(__name__)

_redis_connection = None
_queue = None


def get_redis_connection():
    """Get Redis connection."""
    global _redis_connection
    
    if _redis_connection is None:
        try:
            _redis_connection = redis.from_url(settings.redis_url)
            # Test connection
            _redis_connection.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Background tasks will use in-memory queue.")
            return None
    
    return _redis_connection


def get_queue() -> Optional[Queue]:
    """Get RQ queue instance."""
    global _queue
    
    if _queue is None:
        redis_conn = get_redis_connection()
        if redis_conn:
            _queue = Queue(connection=redis_conn)
            logger.info("RQ queue initialized")
        else:
            logger.warning("RQ queue not available (Redis not configured)")
            return None
    
    return _queue

