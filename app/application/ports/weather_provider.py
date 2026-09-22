"""Application-owned contract for obtaining normalized forecasts."""

from typing import Protocol

from app.domain.models.weather import Coordinates, Forecast


class WeatherProviderError(Exception):
    """Base class for expected failures at the weather provider boundary."""


class WeatherProviderTimeout(WeatherProviderError):
    """The provider did not respond within the configured time limits."""


class WeatherProviderUnavailable(WeatherProviderError):
    """The provider could not be reached or temporarily refused service."""


class WeatherProviderInvalidResponse(WeatherProviderError):
    """The provider rejected the request or returned unusable forecast data."""


class WeatherProvider(Protocol):
    async def get_forecast(
        self, coordinates: Coordinates, *, forecast_days: int
    ) -> Forecast:
        """Return 1-7 UTC calendar days, preserving the requested coordinates.

        Anchor the window to the UTC date when the upstream request starts,
        validate it before returning, and preserve missing measurements as None.
        Translate expected external failures into WeatherProviderError subtypes.
        """
        ...
