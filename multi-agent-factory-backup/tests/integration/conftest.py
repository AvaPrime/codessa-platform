import pytest
import asyncio
import docker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_compose():
    """Start test environment with Docker Compose"""
    with DockerCompose("tests/integration", compose_file_name="docker-compose.test.yml") as compose:
        # Wait for services to be healthy
        compose.wait_for("http://localhost:8000/health")
        yield compose

@pytest.fixture(scope="session")
def test_database():
    """Provide test database connection"""
    with PostgresContainer("ankane/pgvector:v0.5.1") as postgres:
        yield postgres.get_connection_url()

@pytest.fixture
async def api_client(docker_compose):
    """Provide authenticated API client"""
    from httpx import AsyncClient
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Authenticate and get token
        auth_response = await client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        token = auth_response.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client