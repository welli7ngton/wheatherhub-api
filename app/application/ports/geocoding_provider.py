from typing import Protocol

from app.domain.models.location import Location


class GeocodingProviderError(Exception):
    """Expected failure at the geocoding boundary."""


class GeocodingProviderTimeout(GeocodingProviderError):
    pass


class GeocodingProviderUnavailable(GeocodingProviderError):
    pass


class GeocodingProviderInvalidResponse(GeocodingProviderError):
    pass


class GeocodingProvider(Protocol):
    async def search(
        self, name: str, country_code: str, *, limit: int
    ) -> tuple[Location, ...]: ...
