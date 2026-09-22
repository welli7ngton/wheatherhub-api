from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
Percentage = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]


def normalize_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(normalize_utc)]


class ForecastQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: Latitude
    longitude: Longitude
    forecast_days: int = Field(default=1, ge=1, le=7)


class ForecastLocation(BaseModel):
    """Requested coordinates, not the provider's nearest grid cell."""

    latitude: Latitude
    longitude: Longitude


class ForecastUnits(BaseModel):
    temperature: Literal["celsius"] = "celsius"
    humidity: Literal["percent"] = "percent"
    precipitation_probability: Literal["percent"] = "percent"
    wind_speed: Literal["km/h"] = "km/h"


class HourlyForecast(BaseModel):
    time: UtcDatetime
    temperature: Annotated[float, Field(allow_inf_nan=False)] | None
    humidity: Percentage | None
    precipitation_probability: Percentage | None
    wind_speed: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None


class ForecastResponse(BaseModel):
    location: ForecastLocation
    timezone: Literal["UTC"] = "UTC"
    forecast_days: int = Field(ge=1, le=7)
    fetched_at: UtcDatetime = Field(
        description="When WeatherHub retrieved the data, not model issuance time."
    )
    units: ForecastUnits = Field(default_factory=ForecastUnits)
    hourly: list[HourlyForecast] = Field(min_length=24, max_length=168)

    @model_validator(mode="after")
    def validate_hourly_window(self) -> Self:
        if len(self.hourly) != self.forecast_days * 24:
            raise ValueError("Expected 24 hourly records per forecast day")
        start = self.hourly[0].time
        if start != start.replace(hour=0, minute=0, second=0, microsecond=0):
            raise ValueError("Forecast must start at midnight UTC")
        if any(
            point.time != start + timedelta(hours=index)
            for index, point in enumerate(self.hourly)
        ):
            raise ValueError("Forecast hours must be consecutive and ordered")
        return self
