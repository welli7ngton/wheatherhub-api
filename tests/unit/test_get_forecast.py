from datetime import UTC, datetime, timedelta

import pytest

from app.application.ports.weather_provider import (
    WeatherProviderInvalidResponse,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)
from app.application.use_cases.get_forecast import GetForecast
from app.domain.models.weather import Coordinates, Forecast, HourlyForecast


class FakeWeatherProvider:
    """Structural implementation: no inheritance from the protocol required."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[Coordinates, int]] = []

    async def get_forecast(
        self, coordinates: Coordinates, *, forecast_days: int
    ) -> Forecast:
        self.calls.append((coordinates, forecast_days))
        if self.error is not None:
            raise self.error
        start = datetime(2026, 9, 17, tzinfo=UTC)
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


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7])
async def test_get_forecast_preserves_request_and_normalized_data(days: int) -> None:
    provider = FakeWeatherProvider()
    coordinates = Coordinates(latitude=-3.7172, longitude=-38.5433)

    forecast = await GetForecast(provider).execute(coordinates, forecast_days=days)

    assert provider.calls == [(coordinates, days)]
    assert forecast.location == coordinates
    assert forecast.forecast_days == days
    assert len(forecast.hourly) == 24 * days
    assert forecast.hourly[0].precipitation_probability is None
    assert forecast.hourly[0].wind_speed == 0
    assert forecast.fetched_at == datetime(2026, 9, 17, 10, tzinfo=UTC)


@pytest.mark.asyncio
async def test_get_forecast_defaults_to_one_day() -> None:
    provider = FakeWeatherProvider()
    coordinates = Coordinates(latitude=0, longitude=0)

    await GetForecast(provider).execute(coordinates)

    assert provider.calls == [(coordinates, 1)]


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [0, -1, 8, True])
async def test_invalid_horizon_does_not_call_provider(days: int) -> None:
    provider = FakeWeatherProvider()

    with pytest.raises(ValueError, match="forecast_days"):
        await GetForecast(provider).execute(
            Coordinates(latitude=0, longitude=0), forecast_days=days
        )

    assert provider.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        WeatherProviderTimeout("timeout"),
        WeatherProviderUnavailable("unavailable"),
        WeatherProviderInvalidResponse("invalid payload"),
        RuntimeError("unexpected programming error"),
    ],
)
async def test_provider_errors_propagate_without_reclassification(
    error: Exception,
) -> None:
    provider = FakeWeatherProvider(error=error)

    with pytest.raises(type(error)) as caught:
        await GetForecast(provider).execute(Coordinates(latitude=0, longitude=0))

    assert caught.value is error
    assert len(provider.calls) == 1
