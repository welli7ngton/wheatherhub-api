from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float
    timezone: str | None
    country: str | None
    country_code: str | None
    admin1: str | None
