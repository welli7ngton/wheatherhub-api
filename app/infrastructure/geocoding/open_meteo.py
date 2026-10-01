from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.ports.geocoding_provider import (
    GeocodingProviderInvalidResponse,
    GeocodingProviderTimeout,
    GeocodingProviderUnavailable,
)
from app.domain.models.location import Location

NonEmpty = Annotated[str, Field(min_length=1)]


class OpenMeteoLocation(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    name: NonEmpty
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timezone: NonEmpty | None = None
    country: NonEmpty | None = None
    country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None
    admin1: NonEmpty | None = None


class OpenMeteoSearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    results: list[OpenMeteoLocation] = Field(default_factory=list)
    error: Literal[False] = False


class OpenMeteoGeocodingProvider:
    """Borrow a lifespan-owned client; normalize geocoding data at the boundary."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def search(
        self, name: str, country_code: str, *, limit: int
    ) -> tuple[Location, ...]:
        try:
            response = await self._client.get(
                "/v1/search",
                params={
                    "name": name,
                    "count": limit,
                    "countryCode": country_code,
                    "language": "en",
                    "format": "json",
                },
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            raise GeocodingProviderTimeout from exc
        except (httpx.RemoteProtocolError, httpx.DecodingError) as exc:
            raise GeocodingProviderInvalidResponse from exc
        except (httpx.NetworkError, httpx.ProxyError) as exc:
            raise GeocodingProviderUnavailable from exc
        if response.status_code == 429 or response.is_server_error:
            raise GeocodingProviderUnavailable
        if response.status_code != 200:
            raise GeocodingProviderInvalidResponse
        try:
            payload = OpenMeteoSearchResponse.model_validate_json(response.content)
        except ValidationError as exc:
            raise GeocodingProviderInvalidResponse from exc
        if len(payload.results) > limit:
            raise GeocodingProviderInvalidResponse
        return tuple(
            Location(
                name=item.name,
                latitude=item.latitude,
                longitude=item.longitude,
                timezone=item.timezone,
                country=item.country,
                country_code=item.country_code,
                admin1=item.admin1,
            )
            for item in payload.results
        )
