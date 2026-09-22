from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
from pydantic import ValidationError

from app.application.ports.weather_provider import (
    WeatherProviderInvalidResponse,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)
from app.domain.models.weather import Coordinates, Forecast, HourlyForecast
from app.infrastructure.weather.open_meteo_dto import OpenMeteoResponse


def utc_now() -> datetime:
    return datetime.now(UTC)


class OpenMeteoProvider:
    """Normalize provider data; the caller owns client configuration and lifetime.

    The injected client must have the provider base URL and finite timeouts.
    The clock must return timezone-aware datetimes.
    """

    def __init__(
        self, client: httpx.AsyncClient, *, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self._client = client
        self._clock = clock

    def _now(self) -> datetime:
        value = self._clock()
        if value.utcoffset() is None:
            raise ValueError("Provider clock must return an aware datetime")
        return value.astimezone(UTC)

    async def get_forecast(
        self, coordinates: Coordinates, *, forecast_days: int
    ) -> Forecast:
        if type(forecast_days) is not int or not 1 <= forecast_days <= 7:
            raise ValueError("forecast_days must be an integer from 1 through 7")
        start = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=forecast_days - 1)
        try:
            response = await self._client.get(
                "/v1/forecast",
                params={
                    "latitude": coordinates.latitude,
                    "longitude": coordinates.longitude,
                    "hourly": (
                        "temperature_2m,relative_humidity_2m,"
                        "precipitation_probability,wind_speed_10m"
                    ),
                    "timezone": "UTC",
                    "temperature_unit": "celsius",
                    "wind_speed_unit": "kmh",
                    "timeformat": "iso8601",
                    "start_date": start.date().isoformat(),
                    "end_date": end.date().isoformat(),
                },
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            raise WeatherProviderTimeout("Weather provider timed out") from exc
        except (httpx.RemoteProtocolError, httpx.DecodingError) as exc:
            raise WeatherProviderInvalidResponse(
                "Weather provider returned an invalid response"
            ) from exc
        except (httpx.NetworkError, httpx.ProxyError) as exc:
            raise WeatherProviderUnavailable("Weather provider is unavailable") from exc

        fetched_at = self._now()
        if response.status_code == 429 or response.is_server_error:
            raise WeatherProviderUnavailable("Weather provider is unavailable")
        if response.status_code != 200:
            raise WeatherProviderInvalidResponse(
                "Weather provider rejected the request"
            )
        try:
            payload = OpenMeteoResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise WeatherProviderInvalidResponse(
                "Weather provider returned invalid forecast data"
            ) from exc

        hourly = payload.hourly
        count = forecast_days * 24
        arrays = (
            hourly.time,
            hourly.temperature_2m,
            hourly.relative_humidity_2m,
            hourly.precipitation_probability,
            hourly.wind_speed_10m,
        )
        if any(len(values) != count for values in arrays):
            raise WeatherProviderInvalidResponse(
                "Weather provider returned missing hours"
            )
        timestamps = tuple(start + timedelta(hours=index) for index in range(count))
        if hourly.time != [value.strftime("%Y-%m-%dT%H:%M") for value in timestamps]:
            raise WeatherProviderInvalidResponse(
                "Weather provider returned an unexpected forecast window"
            )

        return Forecast(
            location=coordinates,
            forecast_days=forecast_days,
            fetched_at=fetched_at,
            hourly=tuple(
                HourlyForecast(
                    time=value,
                    temperature=hourly.temperature_2m[index],
                    humidity=hourly.relative_humidity_2m[index],
                    precipitation_probability=hourly.precipitation_probability[index],
                    wind_speed=hourly.wind_speed_10m[index],
                )
                for index, value in enumerate(timestamps)
            ),
        )
