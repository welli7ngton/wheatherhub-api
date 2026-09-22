"""Only the provider fields consumed by WeatherHub are modeled here."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Measurement = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Percentage = Annotated[Measurement, Field(ge=0, le=100)]
WindSpeed = Annotated[Measurement, Field(ge=0)]


class OpenMeteoHourly(BaseModel):
    model_config = ConfigDict(strict=True)

    time: list[str]
    temperature_2m: list[Measurement | None]
    relative_humidity_2m: list[Percentage | None]
    precipitation_probability: list[Percentage | None]
    wind_speed_10m: list[WindSpeed | None]


class OpenMeteoUnits(BaseModel):
    time: Literal["iso8601"]
    temperature_2m: Literal["°C"]
    relative_humidity_2m: Literal["%"]
    precipitation_probability: Literal["%"]
    wind_speed_10m: Literal["km/h"]


class OpenMeteoResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    timezone: Literal["UTC", "GMT", "Etc/UTC", "Etc/GMT"]
    utc_offset_seconds: int = Field(ge=0, le=0)
    hourly_units: OpenMeteoUnits
    hourly: OpenMeteoHourly
