#import redis
import fakeredis

redis = fakeredis.FakeRedis()


default_host = "localhost"
default_port = 6379


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
        self._client = None
        print(f"Redis configured: {self.host}:{self.port} (db={self.db})")
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
            print("Redis client initialized")
        return self._client

    
    def get_info(self):
        try:
            response = self.client.ping()
            if response:
                print("Redis connection successful")
            else:
                print("Redis connection failed (no PONG received)")
        except redis.ConnectionError as e:
            print(f"Redis connection error: {e}")
        except Exception as e:
            print(f"Unexpected error testing Redis: {e}")
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
            print(f"Error getting Redis stats: {e}")
            return {}
    

    def close(self):
        try:
            if self._client:
                self._client.close()
                print("Redis client closed")
            if self.pool:
                self.pool.disconnect()
                print("Redis connection pool disconnected")
        except Exception as e:
            print(f"Error closing Redis connection: {e}")


def redis_handle(host = default_host, port = default_port, db = 0, password = None):
    print("Setting up Redis handler.")
    error_data = None, None, None
    try:
        handler = RedisConnectionHandler(host=host, port=port, db=0, password=password)
        # Test connection
        response = handler.get_info()
        if response:
            broker_url = handler.url
            backend_url = handler.url
            print(f"Celery broker URL: {broker_url}")
            print(f"Celery backend URL: {backend_url}")
            return broker_url, backend_url, handler
        else:
            print("Redis connection failed")
            return error_data
            
    except redis.ConnectionError as e:
        print(f"Redis connection error: {e}")
        print("Make sure Redis is running:")
        return error_data
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return error_data