import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import create_app

@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app for testing."""
    return create_app()

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app."""
    return TestClient(app)

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root_endpoint(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()