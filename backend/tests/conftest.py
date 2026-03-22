import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app


@pytest.fixture
def client():
    """Create a synchronous test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an asynchronous test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
