from app.application.ports.geocoding_provider import GeocodingProvider
from app.domain.models.location import Location


class SearchLocation:
    def __init__(self, provider: GeocodingProvider) -> None:
        self._provider = provider

    async def execute(
        self, name: str, country_code: str, *, limit: int = 10
    ) -> tuple[Location, ...]:
        name = name.strip()
        country_code = country_code.strip()

        if not 2 <= len(name) <= 100:
            raise ValueError("name must contain 2-100 characters after trimming")

        if not len(country_code) == 2:
            raise ValueError("invalid country code")

        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer from 1 through 20")
        return await self._provider.search(name, country_code, limit=limit)
