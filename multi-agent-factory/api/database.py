from __future__ import annotations

import os
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis.asyncio as redis
from contextlib import contextmanager

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://maf_user:maf_password@localhost:5432/maf_db"
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for SQLAlchemy models
Base = declarative_base()
metadata = MetaData(schema="maf")
Base.metadata = metadata

# Redis connection pool
redis_pool = None

async def get_redis_pool() -> redis.ConnectionPool:
    """Get Redis connection pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
    return redis_pool

async def get_redis() -> redis.Redis:
    """Get Redis client."""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """Drop all tables in the database."""
    Base.metadata.drop_all(bind=engine)

async def close_redis_pool():
    """Close Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None

# Health check functions
def check_database_health() -> bool:
    """Check if database is healthy."""
    try:
        with get_db_context() as db:
            db.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_redis_health() -> bool:
    """Check if Redis is healthy."""
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        return True
    except Exception:
        return False

# Database initialization
def init_database():
    """Initialize database with tables and default data."""
    try:
        # Import models to ensure they're registered
        from .models import UserModel, RoleModel, UserSessionModel
        
        # Create tables
        create_tables()
        
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return False

# Migration helpers
def get_database_version() -> str:
    """Get current database version."""
    try:
        with get_db_context() as db:
            result = db.execute(
                "SELECT version FROM maf.schema_version ORDER BY applied_at DESC LIMIT 1"
            ).fetchone()
            return result[0] if result else "0.0.0"
    except Exception:
        return "0.0.0"

def set_database_version(version: str) -> bool:
    """Set database version."""
    try:
        with get_db_context() as db:
            db.execute(
                "INSERT INTO maf.schema_version (version, applied_at) VALUES (%s, NOW())",
                (version,)
            )
        return True
    except Exception:
        return False