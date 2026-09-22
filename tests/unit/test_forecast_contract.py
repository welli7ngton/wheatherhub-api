from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.api.schemas.errors import ErrorResponse
from app.api.schemas.weather import ForecastQuery, ForecastResponse


@pytest.mark.parametrize("latitude,longitude", [("-90", "-180"), ("90", "180")])
def test_query_accepts_coordinate_boundaries(latitude: str, longitude: str) -> None:
    query = ForecastQuery.model_validate({"latitude": latitude, "longitude": longitude})
    assert query.latitude == float(latitude)
    assert query.longitude == float(longitude)
    assert query.forecast_days == 1


@pytest.mark.parametrize(
    "override",
    [
        {"latitude": "90.1"},
        {"latitude": "-90.1"},
        {"longitude": "180.1"},
        {"longitude": "-180.1"},
        {"latitude": "nan"},
        {"longitude": "inf"},
        {"latitude": "Fortaleza"},
        {"forecast_days": "0"},
        {"forecast_days": "8"},
        {"forecast_days": "1.5"},
        {"timezone": "America/Fortaleza"},
    ],
)
def test_query_rejects_invalid_parameters(override: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        ForecastQuery.model_validate({"latitude": "0", "longitude": "0", **override})


@pytest.mark.parametrize("missing", ["latitude", "longitude"])
def test_coordinates_are_required(missing: str) -> None:
    values = {"latitude": "0", "longitude": "0"}
    del values[missing]
    with pytest.raises(ValidationError):
        ForecastQuery.model_validate(values)


def response_payload(days: int = 1) -> dict[str, object]:
    start = datetime(2026, 9, 16, tzinfo=UTC)
    return {
        "location": {"latitude": -3.7172, "longitude": -38.5433},
        "forecast_days": days,
        "fetched_at": "2026-09-16T07:05:00-03:00",
        "hourly": [
            {
                "time": start + timedelta(hours=index),
                "temperature": 27.4,
                "humidity": 80,
                "precipitation_probability": None,
                "wind_speed": 0,
            }
            for index in range(days * 24)
        ],
    }


@pytest.mark.parametrize("days", [1, 7])
def test_response_serializes_utc_and_preserves_missing_values(days: int) -> None:
    response = ForecastResponse.model_validate(response_payload(days))
    serialized = response.model_dump(mode="json")
    assert serialized["fetched_at"] == "2026-09-16T10:05:00Z"
    assert len(response.hourly) == days * 24
    assert response.hourly[0].precipitation_probability is None
    assert response.hourly[0].wind_speed == 0
    assert response.units.temperature == "celsius"


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unordered", "midday"])
def test_response_rejects_invalid_hourly_windows(failure: str) -> None:
    response = ForecastResponse.model_validate(response_payload())
    if failure == "missing":
        response.hourly.pop()
    elif failure == "duplicate":
        response.hourly[1].time = response.hourly[0].time
    elif failure == "unordered":
        response.hourly.reverse()
    else:
        for point in response.hourly:
            point.time += timedelta(hours=12)
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(response.model_dump())


@pytest.mark.parametrize(
    "override",
    [
        {"humidity": 101},
        {"precipitation_probability": -1},
        {"wind_speed": -1},
        {"temperature": float("nan")},
        {"time": "2026-09-16T00:00:00"},
    ],
)
def test_response_rejects_invalid_measurements(override: dict[str, object]) -> None:
    payload = ForecastResponse.model_validate(response_payload()).model_dump()
    payload["hourly"][0].update(override)
    with pytest.raises(ValidationError):
        ForecastResponse.model_validate(payload)


def test_error_envelope_round_trip() -> None:
    payload = {
        "error": {
            "code": "INVALID_COORDINATES",
            "message": "Latitude and longitude must be valid coordinates.",
            "request_id": "72174a7b-a22b-4269-8674-8ce1a1fdf835",
        }
    }
    assert ErrorResponse.model_validate(payload).model_dump(mode="json") == payload
