from pydantic import BaseSettings

class TestSettings(BaseSettings):
    # Database
    test_postgres_uri: str = "postgresql://test_user:test_pass@localhost:5433/test_factory"
    test_redis_host: str = "localhost"
    test_redis_port: int = 6380
    
    # API
    test_api_base_url: str = "http://localhost:8001"
    test_jwt_secret: str = "test-secret-key"
    
    # Testing
    test_timeout: int = 30
    test_retry_attempts: int = 3
    
    class Config:
        env_file = ".env.test"

test_settings = TestSettings()