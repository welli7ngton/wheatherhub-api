from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.application import create_application
from app.api.dependencies import get_search_location_use_case
from app.application.ports.geocoding_provider import (
    GeocodingProviderInvalidResponse,
    GeocodingProviderTimeout,
    GeocodingProviderUnavailable,
)
from app.application.use_cases.search_location import SearchLocation
from app.config.settings import Settings
from app.domain.models.location import Location


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self.error: Exception | None = None
        self.results: tuple[Location, ...] = (
            Location(
                "Fortaleza", -3.71, -38.54, "America/Fortaleza", "Brazil", "BR", "Ceará"
            ),
        )

    async def search(
        self, name: str, country_code: str, *, limit: int
    ) -> tuple[Location, ...]:
        self.calls.append((name, country_code, limit))
        if self.error:
            raise self.error
        return self.results


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def locations_client(provider: FakeProvider) -> Iterator[TestClient]:
    app = create_application(Settings(debug=False))
    app.dependency_overrides[get_search_location_use_case] = lambda: SearchLocation(
        provider
    )
    with TestClient(app) as client:
        yield client


def test_search(locations_client: TestClient, provider: FakeProvider) -> None:
    response = locations_client.get(
        "/api/v1/locations/search",
        params={"name": " Fortaleza ", "country_code": " BR ", "limit": 2},
    )
    assert response.status_code == 200
    assert provider.calls == [("Fortaleza", "BR", 2)]
    assert response.json()["results"][0]["country_code"] == "BR"
    assert response.headers["X-Request-ID"]


def test_no_matches(locations_client: TestClient, provider: FakeProvider) -> None:
    provider.results = ()
    response = locations_client.get(
        "/api/v1/locations/search?name=unknown&country_code=BR"
    )
    assert response.status_code == 200
    assert response.json() == {"results": []}
    assert provider.calls == [("unknown", "BR", 10)]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "country_code=BR",
        "name=city",
        "q=city&country_code=BR",
        "name=city&q=city&country_code=BR",
        "name=a&country_code=BR",
        "name=%20%20&country_code=BR",
        "name=" + "a" * 101 + "&country_code=BR",
        "name=city&country_code=",
        "name=city&country_code=B",
        "name=city&country_code=BRA",
        "name=city&country_code=%20%20",
        "name=city&country_code=BR&country_code=BR",
        "name=city&country_code=BR&limit=0",
        "name=city&country_code=BR&limit=21",
        "name=city&country_code=BR&limit=abc",
        "name=city&country_code=BR&limit=1.5",
        "name=city&name=city&country_code=BR",
        "name=city&country_code=BR&limit=2&limit=2",
        "name=city&country_code=BR&extra=x",
        "name=city&country_code=BR&latitude=1&latitude=2",
    ],
)
def test_invalid_query(
    locations_client: TestClient, provider: FakeProvider, query: str
) -> None:
    response = locations_client.get("/api/v1/locations/search?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QUERY"
    assert provider.calls == []


@pytest.mark.parametrize(
    "error,status,code",
    [
        (GeocodingProviderTimeout, 504, "GEOCODING_PROVIDER_TIMEOUT"),
        (GeocodingProviderUnavailable, 503, "GEOCODING_PROVIDER_UNAVAILABLE"),
        (GeocodingProviderInvalidResponse, 502, "GEOCODING_PROVIDER_INVALID_RESPONSE"),
        (RuntimeError, 500, "INTERNAL_ERROR"),
    ],
)
def test_errors(
    locations_client: TestClient,
    provider: FakeProvider,
    error: type[Exception],
    status: int,
    code: str,
) -> None:
    provider.error = error("private details")
    response = locations_client.get(
        "/api/v1/locations/search?name=city&country_code=BR"
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "private details" not in response.text
