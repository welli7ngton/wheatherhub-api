import pytest

from app.application.ports.geocoding_provider import GeocodingProviderUnavailable
from app.application.use_cases.search_location import SearchLocation
from app.domain.models.location import Location


class FakeProvider:
    async def search(
        self, name: str, country_code: str, *, limit: int
    ) -> tuple[Location, ...]:
        assert name == "Fortaleza"
        assert country_code == "BR"
        assert limit == 10
        raise GeocodingProviderUnavailable


@pytest.mark.asyncio
async def test_normalizes_query_and_propagates_failure() -> None:
    with pytest.raises(GeocodingProviderUnavailable):
        await SearchLocation(FakeProvider()).execute(" Fortaleza ", " BR ")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,limit",
    [
        (" ", 10),
        ("a", 10),
        ("x" * 101, 10),
        ("Fortaleza", 0),
        ("Fortaleza", 21),
        ("Fortaleza", True),
    ],
)
async def test_rejects_invalid_input_before_provider(query: str, limit: int) -> None:
    with pytest.raises(ValueError):
        await SearchLocation(FakeProvider()).execute(query, "BR", limit=limit)


@pytest.mark.asyncio
@pytest.mark.parametrize("country_code", ["", " ", "B", "BRA", " B "])
async def test_rejects_invalid_country_before_provider(country_code: str) -> None:
    with pytest.raises(ValueError, match="invalid country code"):
        await SearchLocation(FakeProvider()).execute("Fortaleza", country_code)
