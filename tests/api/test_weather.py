import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.application import create_application
from app.api.dependencies import get_forecast_use_case
from app.api.schemas.errors import ErrorResponse
from app.application.ports.weather_provider import (
    WeatherProviderInvalidResponse,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)
from app.application.use_cases.get_forecast import GetForecast
from app.config.settings import Settings
from app.domain.models.weather import Coordinates, Forecast, HourlyForecast

URL = "/api/v1/weather/forecast"


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[Coordinates, int]] = []
        self.error: Exception | None = None

    async def get_forecast(
        self, coordinates: Coordinates, *, forecast_days: int
    ) -> Forecast:
        self.calls.append((coordinates, forecast_days))
        if self.error is not None:
            raise self.error
        start = datetime(2026, 9, 22, tzinfo=UTC)
        return Forecast(
            location=coordinates,
            forecast_days=forecast_days,
            fetched_at=start + timedelta(hours=10),
            hourly=tuple(
                HourlyForecast(
                    time=start + timedelta(hours=index),
                    temperature=27.4,
                    humidity=80,
                    precipitation_probability=None,
                    wind_speed=0,
                )
                for index in range(forecast_days * 24)
            ),
        )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def forecast_client(provider: FakeProvider) -> Iterator[TestClient]:
    application = create_application(Settings(debug=False))
    use_case = GetForecast(provider)
    application.dependency_overrides[get_forecast_use_case] = lambda: use_case
    with TestClient(application) as client:
        yield client


@pytest.mark.parametrize("days", [None, 1, 7])
def test_forecast_success(
    forecast_client: TestClient, provider: FakeProvider, days: int | None
) -> None:
    params = {"latitude": "-3.7172", "longitude": "-38.5433"}
    if days is not None:
        params["forecast_days"] = str(days)
    response = forecast_client.get(URL, params=params)
    assert response.status_code == 200
    assert UUID(response.headers["X-Request-ID"]).version == 4
    count = days if days is not None else 1
    assert provider.calls == [(Coordinates(-3.7172, -38.5433), count)]
    body = response.json()
    assert body["location"] == {"latitude": -3.7172, "longitude": -38.5433}
    assert body["forecast_days"] == count
    assert body["timezone"] == "UTC"
    assert body["fetched_at"] == "2026-09-22T10:00:00Z"
    assert body["units"] == {
        "temperature": "celsius",
        "humidity": "percent",
        "precipitation_probability": "percent",
        "wind_speed": "km/h",
    }
    assert len(body["hourly"]) == count * 24
    start = datetime(2026, 9, 22, tzinfo=UTC)
    for index, point in enumerate(body["hourly"]):
        assert point == {
            "time": (start + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
            "temperature": 27.4,
            "humidity": 80,
            "precipitation_probability": None,
            "wind_speed": 0,
        }


@pytest.mark.parametrize(
    "query",
    [
        "",
        "latitude=0",
        "longitude=0",
        "latitude=bad&longitude=0",
        "latitude=90.1&longitude=0",
        "latitude=-90.1&longitude=0",
        "latitude=0&longitude=180.1",
        "latitude=0&longitude=-180.1",
        "latitude=nan&longitude=0",
        "latitude=0&longitude=inf",
        "latitude=0&longitude=0&forecast_days=0",
        "latitude=0&longitude=0&forecast_days=8",
        "latitude=0&longitude=0&forecast_days=1.5",
        "latitude=0&longitude=0&forecast_days=bad",
        "latitude=0&longitude=0&timezone=UTC",
        "latitude=0&latitude=1&longitude=0",
        "latitude=0&longitude=0&longitude=0",
        "latitude=0&longitude=0&forecast_days=1&forecast_days=7",
        "latitude=0&longitude=0&forecast_days=1&forecast_days=1",
        "latitude=bad&latitude=0&longitude=0",
        "latitude=0&latitude=bad&longitude=0",
    ],
)
def test_invalid_query_never_calls_provider(
    forecast_client: TestClient, provider: FakeProvider, query: str
) -> None:
    response = forecast_client.get(f"{URL}?{query}")
    assert response.status_code == 422
    assert_error(
        response.text,
        response.headers["X-Request-ID"],
        response.json()["error"]["code"],
    )
    assert provider.calls == []


@pytest.mark.parametrize("latitude,longitude", [("-90", "-180"), ("90", "180")])
def test_coordinate_boundaries(
    forecast_client: TestClient,
    provider: FakeProvider,
    latitude: str,
    longitude: str,
) -> None:
    response = forecast_client.get(
        URL, params={"latitude": latitude, "longitude": longitude}
    )
    assert response.status_code == 200
    assert provider.calls == [(Coordinates(float(latitude), float(longitude)), 1)]


def test_forecast_openapi(forecast_client: TestClient) -> None:
    schema = forecast_client.get("/openapi.json").json()
    operation = schema["paths"][URL]["get"]
    parameters = {item["name"]: item for item in operation["parameters"]}
    assert set(parameters) == {"latitude", "longitude", "forecast_days"}
    assert all(item["in"] == "query" for item in parameters.values())
    assert parameters["latitude"]["required"] is True
    assert parameters["longitude"]["required"] is True
    assert parameters["forecast_days"]["required"] is False
    assert parameters["forecast_days"]["schema"]["default"] == 1
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ForecastResponse"
    }
    for status in (200, 422, 500, 502, 503, 504):
        documented = operation["responses"][str(status)]
        assert documented["headers"]["X-Request-ID"]["schema"]["format"] == "uuid"
        if status != 200:
            assert documented["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ErrorResponse"
            }


def assert_error(text: str, request_id: str, code: str) -> None:
    body = json.loads(text)
    assert ErrorResponse.model_validate(body).model_dump(mode="json") == body
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["error"]["request_id"] == request_id
    assert UUID(request_id).version == 4


@pytest.mark.parametrize(
    "query,code",
    [
        ("", "INVALID_COORDINATES"),
        ("latitude=bad&longitude=0&forecast_days=8", "INVALID_COORDINATES"),
        ("latitude=0&latitude=0&longitude=0&forecast_days=8", "INVALID_COORDINATES"),
        ("latitude=0&longitude=0&longitude=1&extra=x", "INVALID_COORDINATES"),
        ("latitude=0&longitude=nan&extra=x", "INVALID_COORDINATES"),
        ("latitude=0&longitude=0&forecast_days=8", "INVALID_QUERY"),
        ("latitude=0&longitude=0&extra=x", "INVALID_QUERY"),
        ("latitude=0&longitude=0&extra=x&extra=x", "INVALID_QUERY"),
        ("latitude=0&longitude=0&forecast_days=1&forecast_days=1", "INVALID_QUERY"),
    ],
)
def test_validation_error_precedence(
    forecast_client: TestClient, provider: FakeProvider, query: str, code: str
) -> None:
    response = forecast_client.get(f"{URL}?{query}")
    assert response.status_code == 422
    assert_error(response.text, response.headers["X-Request-ID"], code)
    assert provider.calls == []


@pytest.mark.parametrize(
    "error,status,code",
    [
        (WeatherProviderTimeout("private upstream"), 504, "WEATHER_PROVIDER_TIMEOUT"),
        (
            WeatherProviderUnavailable("private upstream"),
            503,
            "WEATHER_PROVIDER_UNAVAILABLE",
        ),
        (
            WeatherProviderInvalidResponse("private upstream"),
            502,
            "WEATHER_PROVIDER_INVALID_RESPONSE",
        ),
    ],
)
def test_provider_errors(
    forecast_client: TestClient,
    provider: FakeProvider,
    error: Exception,
    status: int,
    code: str,
) -> None:
    provider.error = error
    response = forecast_client.get(f"{URL}?latitude=0&longitude=0")
    assert response.status_code == status
    assert_error(response.text, response.headers["X-Request-ID"], code)
    assert "private upstream" not in response.text
    assert len(provider.calls) == 1


@pytest.mark.parametrize("debug", [False, True])
def test_unexpected_error_is_safe_and_logged(
    provider: FakeProvider, caplog: pytest.LogCaptureFixture, debug: bool
) -> None:
    provider.error = RuntimeError("private internal details")
    application = create_application(Settings(debug=debug))
    application.dependency_overrides[get_forecast_use_case] = lambda: GetForecast(
        provider
    )
    with TestClient(application) as client:
        response = client.get(f"{URL}?latitude=0&longitude=0")
    assert response.status_code == 500
    assert_error(response.text, response.headers["X-Request-ID"], "INTERNAL_ERROR")
    assert "private internal details" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Request-ID"] in caplog.text
    assert "private internal details" in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_request_ids_are_generated_per_request(forecast_client: TestClient) -> None:
    supplied = "72174a7b-a22b-4269-8674-8ce1a1fdf835"
    responses = [
        forecast_client.get(path, headers={"X-Request-ID": supplied})
        for path in (f"{URL}?latitude=0&longitude=0", URL, "/health")
    ]
    identifiers = {response.headers["X-Request-ID"] for response in responses}
    assert len(identifiers) == 3
    assert supplied not in identifiers
    assert all(UUID(value).version == 4 for value in identifiers)
