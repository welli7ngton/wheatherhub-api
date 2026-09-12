import pytest
from fastapi.testclient import TestClient
from app.api.application import app


@pytest.fixture
def client():
    return TestClient(app=app)