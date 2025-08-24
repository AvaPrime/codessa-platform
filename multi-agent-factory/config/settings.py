from pydantic import BaseSettings, Field, validator
from typing import Optional, List
import os
from pathlib import Path

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    user: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    host: str = Field(default="db", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="factory", description="Database name")
    
    @property
    def uri(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    class Config:
        env_prefix = "POSTGRES_"

class RedisSettings(BaseSettings):
    """Redis configuration"""
    host: str = Field(default="redis", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    
    class Config:
        env_prefix = "REDIS_"

class NATSSettings(BaseSettings):
    """NATS configuration"""
    url: str = Field(default="nats://nats:4222", description="NATS server URL")
    cluster_routes: Optional[str] = Field(default=None, description="NATS cluster routes")
    hmac_secret: str = Field(default="default-secret", description="NATS HMAC secret")
    
    class Config:
        env_prefix = "NATS_"

class TemporalSettings(BaseSettings):
    """Temporal configuration"""
    host: str = Field(default="temporal", description="Temporal server host")
    port: int = Field(default=7233, description="Temporal server port")
    namespace: str = Field(default="default", description="Temporal namespace")
    
    class Config:
        env_prefix = "TEMPORAL_"

class LLMSettings(BaseSettings):
    """LLM provider configuration"""
    openai_api_key: str = Field(..., description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(default=None, description="Google API key")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    generation_model: str = Field(default="gpt-4o-mini", description="Generation model")
    
    class Config:
        env_prefix = ""

class SecuritySettings(BaseSettings):
    """Security configuration"""
    jwt_secret: str = Field(..., description="JWT signing secret")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")
    encryption_key: str = Field(..., description="Encryption key for sensitive data")
    task_signing_secret: str = Field(..., description="Task signing secret")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], description="CORS allowed origins")
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_prefix = ""

class ObservabilitySettings(BaseSettings):
    """Observability configuration"""
    jaeger_host: str = Field(default="jaeger", description="Jaeger agent host")
    jaeger_port: int = Field(default=6831, description="Jaeger agent port")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    enable_tracing: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    
    class Config:
        env_prefix = "OBSERVABILITY_"

class VectorStoreSettings(BaseSettings):
    """Vector store configuration"""
    embedding_dim: int = Field(default=1536, description="Embedding dimension")
    table_name: str = Field(default="documents", description="Vector table name")
    ivfflat_lists: int = Field(default=100, description="IVFFlat index lists")
    
    class Config:
        env_prefix = "VECTOR_"

class ResourceGovernanceSettings(BaseSettings):
    """Resource governance configuration"""
    enabled: bool = Field(default=True, description="Enable resource governance")
    config_path: str = Field(default="config/resource_governance.yaml", description="Governance config path")
    
    # Budget settings
    monthly_budget_usd: float = Field(default=5000.0, description="Monthly budget in USD")
    budget_alert_webhook: Optional[str] = Field(default=None, description="Budget alert webhook URL")
    
    # Resource limits
    enforce_limits: bool = Field(default=True, description="Enforce resource limits")
    auto_scale_enabled: bool = Field(default=True, description="Enable auto-scaling")
    
    # Cost tracking
    cost_tracking_enabled: bool = Field(default=True, description="Enable cost tracking")
    cost_allocation_tags: List[str] = Field(default=["team", "project", "environment"], description="Cost allocation tags")
    
    class Config:
        env_prefix = "GOVERNANCE_"

class AppSettings(BaseSettings):
    """Main application settings"""
    env: str = Field(default="dev", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Debug mode")
    api_port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=2, description="Number of worker processes")
    task_ttl_seconds: int = Field(default=7*24*3600, description="Task TTL in seconds")
    
    # Nested settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    nats: NATSSettings = NATSSettings()
    temporal: TemporalSettings = TemporalSettings()
    llm: LLMSettings = LLMSettings()
    security: SecuritySettings = SecuritySettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    
    # Add resource governance settings
    governance: ResourceGovernanceSettings = ResourceGovernanceSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def dump_config(self) -> dict:
        """Dump configuration for debugging (excluding secrets)"""
        config = self.dict()
        
        # Mask sensitive fields
        sensitive_fields = [
            'llm.openai_api_key', 'llm.anthropic_api_key', 'llm.google_api_key',
            'security.jwt_secret', 'security.encryption_key', 'security.task_signing_secret',
            'database.password', 'redis.password', 'nats.hmac_secret'
        ]
        
        for field_path in sensitive_fields:
            keys = field_path.split('.')
            current = config
            for key in keys[:-1]:
                if key in current:
                    current = current[key]
                else:
                    break
            else:
                if keys[-1] in current and current[keys[-1]]:
                    current[keys[-1]] = "***MASKED***"
        
        return config

# Global settings instance
settings = AppSettings()