from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.application import create_application
from app.config.settings import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(app_name="WeatherHub Test", debug=False)
    with TestClient(create_application(settings)) as client:
        yield client
