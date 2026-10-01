from pydantic import BaseModel, ConfigDict, Field


class LocationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=100)
    country_code: str = Field(min_length=2, max_length=2)
    limit: int = Field(default=10, ge=1, le=20)


class LocationResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str | None
    country: str | None
    country_code: str | None
    admin1: str | None


class LocationSearchResponse(BaseModel):
    results: list[LocationResponse]
