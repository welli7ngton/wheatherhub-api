import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from app.application.ports.weather_provider import (
    WeatherProvider,
    WeatherProviderInvalidResponse,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)
from app.domain.models.weather import Coordinates
from app.infrastructure.weather.open_meteo import OpenMeteoProvider

START = datetime(2026, 9, 17, tzinfo=UTC)
COORDINATES = Coordinates(latitude=-3.7172, longitude=-38.5433)


def payload(days: int = 1) -> dict[str, Any]:
    return {
        "latitude": -3.75,
        "longitude": -38.5,
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "precipitation_probability": "%",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": [
                (START + timedelta(hours=index)).strftime("%Y-%m-%dT%H:%M")
                for index in range(days * 24)
            ],
            "temperature_2m": [27.4] * (days * 24),
            "relative_humidity_2m": [80] * (days * 24),
            "precipitation_probability": [None] * (days * 24),
            "wind_speed_10m": [0] * (days * 24),
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7])
async def test_request_and_normalization_across_midnight(days: int) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload(days))

    before = START + timedelta(hours=23, minutes=59)
    after = START + timedelta(days=1, seconds=1)
    clock = iter([before, after])
    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(respond),
    ) as client:
        provider: WeatherProvider = OpenMeteoProvider(client, clock=lambda: next(clock))
        forecast = await provider.get_forecast(COORDINATES, forecast_days=days)
        assert not client.is_closed

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/v1/forecast"
    assert dict(request.url.params) == {
        "latitude": "-3.7172",
        "longitude": "-38.5433",
        "hourly": (
            "temperature_2m,relative_humidity_2m,"
            "precipitation_probability,wind_speed_10m"
        ),
        "timezone": "UTC",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "timeformat": "iso8601",
        "start_date": "2026-09-17",
        "end_date": (START + timedelta(days=days - 1)).date().isoformat(),
    }
    assert forecast.location == COORDINATES
    assert forecast.forecast_days == days
    assert forecast.fetched_at == after
    assert len(forecast.hourly) == days * 24
    assert forecast.hourly[0].time == START
    assert forecast.hourly[-1].time == START + timedelta(hours=days * 24 - 1)
    assert forecast.hourly[0].temperature == 27.4
    assert forecast.hourly[0].humidity == 80
    assert forecast.hourly[0].precipitation_probability is None
    assert forecast.hourly[0].wind_speed == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 404, 302, 204, 429, 500, 503])
async def test_http_failures_are_translated_without_following_redirects(
    status: int,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status, text="private upstream details", headers={"location": "/elsewhere"}
        )

    expected = (
        WeatherProviderUnavailable
        if status == 429 or status >= 500
        else WeatherProviderInvalidResponse
    )
    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(respond),
        follow_redirects=True,
    ) as client:
        with pytest.raises(expected) as caught:
            await OpenMeteoProvider(client, clock=lambda: START).get_forecast(
                COORDINATES, forecast_days=1
            )
    assert "private upstream details" not in str(caught.value)
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ConnectTimeout, WeatherProviderTimeout),
        (httpx.ReadTimeout, WeatherProviderTimeout),
        (httpx.WriteTimeout, WeatherProviderTimeout),
        (httpx.PoolTimeout, WeatherProviderTimeout),
        (httpx.ConnectError, WeatherProviderUnavailable),
        (httpx.ReadError, WeatherProviderUnavailable),
        (httpx.ProxyError, WeatherProviderUnavailable),
        (httpx.RemoteProtocolError, WeatherProviderInvalidResponse),
        (httpx.DecodingError, WeatherProviderInvalidResponse),
        (httpx.LocalProtocolError, httpx.LocalProtocolError),
        (RuntimeError, RuntimeError),
    ],
)
async def test_transport_failures(
    error: type[Exception], expected: type[Exception]
) -> None:
    original = error("internal details")

    def fail(request: httpx.Request) -> httpx.Response:
        raise original

    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com", transport=httpx.MockTransport(fail)
    ) as client:
        with pytest.raises(expected) as caught:
            await OpenMeteoProvider(client, clock=lambda: START).get_forecast(
                COORDINATES, forecast_days=1
            )
    if error in (RuntimeError, httpx.LocalProtocolError):
        assert caught.value is original
    else:
        assert caught.value.__cause__ is original
        assert "internal details" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("hourly"),
        lambda p: p["hourly"].pop("temperature_2m"),
        lambda p: p["hourly"]["temperature_2m"].pop(),
        lambda p: p["hourly"]["time"].pop(),
        lambda p: p["hourly"]["time"].reverse(),
        lambda p: p["hourly"]["time"].__setitem__(1, p["hourly"]["time"][0]),
        lambda p: p["hourly"].__setitem__("time", ["2026-09-18T00:00"] * 24),
        lambda p: p["hourly"]["time"].__setitem__(0, "invalid"),
        lambda p: p["hourly"]["temperature_2m"].__setitem__(0, "27.4"),
        lambda p: p["hourly"]["temperature_2m"].__setitem__(0, True),
        lambda p: p["hourly"]["temperature_2m"].__setitem__(0, float("nan")),
        lambda p: p["hourly"]["temperature_2m"].__setitem__(0, float("inf")),
        lambda p: p["hourly"]["temperature_2m"].__setitem__(0, float("-inf")),
        lambda p: p["hourly"]["relative_humidity_2m"].__setitem__(0, 101),
        lambda p: p["hourly"]["precipitation_probability"].__setitem__(0, -1),
        lambda p: p["hourly"]["wind_speed_10m"].__setitem__(0, -1),
        lambda p: p["hourly_units"].__setitem__("temperature_2m", "°F"),
        lambda p: p["hourly_units"].__setitem__("wind_speed_10m", "mph"),
        lambda p: p["hourly_units"].pop("relative_humidity_2m"),
        lambda p: p.__setitem__("utc_offset_seconds", 3600),
        lambda p: p.__setitem__("utc_offset_seconds", False),
        lambda p: p.__setitem__("timezone", "Europe/Berlin"),
    ],
)
async def test_invalid_payloads(mutate: Callable[[dict[str, Any]], object]) -> None:
    data = payload()
    mutate(data)
    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=json.dumps(data))
        ),
    ) as client:
        with pytest.raises(WeatherProviderInvalidResponse):
            await OpenMeteoProvider(client, clock=lambda: START).get_forecast(
                COORDINATES, forecast_days=1
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"not json", b"null", b"[]", b"{}"])
async def test_invalid_json_or_shape(body: bytes) -> None:
    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=body)
        ),
    ) as client:
        with pytest.raises(WeatherProviderInvalidResponse):
            await OpenMeteoProvider(client, clock=lambda: START).get_forecast(
                COORDINATES, forecast_days=1
            )


@pytest.mark.asyncio
async def test_all_measurements_can_be_missing() -> None:
    data = payload()
    for name, values in data["hourly"].items():
        if name != "time":
            values[0] = None
    async with httpx.AsyncClient(
        base_url="https://api.open-meteo.com",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)),
    ) as client:
        forecast = await OpenMeteoProvider(client, clock=lambda: START).get_forecast(
            COORDINATES, forecast_days=1
        )
    first = forecast.hourly[0]
    assert first.temperature is None
    assert first.humidity is None
    assert first.precipitation_probability is None
    assert first.wind_speed is None
