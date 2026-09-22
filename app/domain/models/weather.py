"""Normalized weather data, independent of HTTP and provider payloads.

Callers validate coordinates before use. Providers validate measurements and
calendar windows before constructing forecasts. All timestamps are aware UTC;
temperature is Celsius, percentages are 0-100, and wind speed is km/h.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    time: datetime
    temperature: float | None
    humidity: float | None
    precipitation_probability: float | None
    wind_speed: float | None


@dataclass(frozen=True, slots=True)
class Forecast:
    """A UTC calendar window at the requested, rather than grid, coordinates.

    Hourly records are consecutive, starting at midnight, with 24 per day.
    ``fetched_at`` records retrieval time, not weather model issuance time.
    """

    location: Coordinates
    forecast_days: int
    fetched_at: datetime
    hourly: tuple[HourlyForecast, ...]
