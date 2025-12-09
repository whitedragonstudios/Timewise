import redis
from typing import Optional
import logging

# Setup logging for Redis operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisConnectionHandler: 
    def __init__(self, host = "localhost", port = 6379, db = 0, password = None):
        # Default connection parameters
        self.host = host or "localhost"
        self.port = port or 6379
        self.db = db or 0
        self.password = password or "stoic"
        self.decode_responses = True
        
        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            max_connections=50,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30)
        # Create Redis client using the connection pool
        self._client: Optional[redis.Redis] = None
        logger.info(f"Redis configured: {self.host}:{self.port} (db={self.db})")
        # Get url of redis server
        if self.password:
            url = f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        else:
            url = f"redis://{self.host}:{self.port}/{self.db}"
        self.url =  url
    
    @property
    def client(self):
        if self._client is None:
            self._client = redis.Redis(connection_pool=self.pool)
            logger.info("Redis client initialized")
        return self._client

    
    def get_info(self):
        try:
            response = self.client.ping()
            if response:
                logger.info("Redis connection successful")
            else:
                logger.error("Redis connection failed (no PONG received)")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error testing Redis: {e}")
        try:
            info = self.client.info()
            connection_info = {
                'version': info.get('redis_version'),
                'connected clients': info.get('connected_clients'),
                'used memory human': info.get('used_memory_human'),
                'total commands': info.get('total_commands_processed'),
                'uptime': f"{info.get('uptime_in_seconds')} seconds",
                'uptime': f"{info.get('uptime_in_days')} days"}
            for k,v in connection_info.items():
                print(f"{k} ==> {v}")
            return connection_info
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {}
    

    def close(self):
        # redis_handler = RedisConnectionHandler()
        # redis_handler.close()  # Clean shutdown
        try:
            if self._client:
                self._client.close()
                logger.info("Redis client closed")
            if self.pool:
                self.pool.disconnect()
                logger.info("Redis connection pool disconnected")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


def redis_handler():
    handle = RedisConnectionHandler()
    logger.info("Setting up Redis for Celery.")
    # Test connection
    try:
        response = handle.get_info()
        if response:
            logger.info("Redis connection verified for Celery")    
            broker_url = handle.url
            backend_url = handle.url
            
            logger.info(f"Celery broker URL: {broker_url}")
            logger.info(f"Celery backend URL: {backend_url}")
            
            return broker_url, backend_url
        else:
            logger.error("Redis connection failed - cannot setup Celery")
            return None, None
            
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None, None