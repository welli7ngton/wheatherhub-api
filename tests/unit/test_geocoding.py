import httpx
import pytest

from app.application.ports.geocoding_provider import (
    GeocodingProviderInvalidResponse,
    GeocodingProviderTimeout,
    GeocodingProviderUnavailable,
)
from app.infrastructure.geocoding.open_meteo import OpenMeteoGeocodingProvider


@pytest.mark.asyncio
async def test_normalizes_multiple_locations_and_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        assert dict(request.url.params) == {
            "name": "São Paulo",
            "count": "2",
            "countryCode": "BR",
            "language": "en",
            "format": "json",
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "São Paulo",
                        "latitude": -23.55,
                        "longitude": -46.63,
                        "timezone": "America/Sao_Paulo",
                        "country": "Brazil",
                        "country_code": "BR",
                        "admin1": "São Paulo",
                        "id": 123,
                    },
                    {"name": "Other", "latitude": 0, "longitude": 0},
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="https://geo.example", transport=httpx.MockTransport(handler)
    ) as client:
        results = await OpenMeteoGeocodingProvider(client).search(
            "São Paulo", "BR", limit=2
        )
        assert len(results) == 2
        assert results[0].country_code == "BR"
        assert results[1].latitude == 0
        assert results[1].timezone is None
        assert not client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"results": []}])
async def test_empty_search(payload: dict[str, object]) -> None:
    async with httpx.AsyncClient(
        base_url="https://geo.example",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    ) as client:
        assert (
            await OpenMeteoGeocodingProvider(client).search("unknown", "BR", limit=10)
            == ()
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"results": None},
        {"results": [{}]},
        {"error": True},
        [],
        {"results": [{"name": "X", "latitude": 91, "longitude": 0}]},
        {"results": [{"name": "X", "latitude": "0", "longitude": 0}]},
        {"results": [{"name": " ", "latitude": 0, "longitude": 0}]},
        {"results": [{"name": "X", "latitude": 0, "longitude": 181}]},
        {
            "results": [
                {"name": "X", "latitude": 0, "longitude": 0, "country_code": "BRA"}
            ]
        },
        {"results": [{"name": "X", "latitude": 0, "longitude": 0}] * 2},
    ],
)
async def test_invalid_payload(payload: object) -> None:
    async with httpx.AsyncClient(
        base_url="https://geo.example",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)),
    ) as client:
        with pytest.raises(GeocodingProviderInvalidResponse):
            await OpenMeteoGeocodingProvider(client).search("city", "BR", limit=1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,error",
    [
        (429, GeocodingProviderUnavailable),
        (500, GeocodingProviderUnavailable),
        (400, GeocodingProviderInvalidResponse),
        (302, GeocodingProviderInvalidResponse),
        (200, GeocodingProviderInvalidResponse),
    ],
)
async def test_http_failure(status: int, error: type[Exception]) -> None:
    async with httpx.AsyncClient(
        base_url="https://geo.example",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, text="not json")
        ),
    ) as client:
        with pytest.raises(error):
            await OpenMeteoGeocodingProvider(client).search("city", "BR", limit=10)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,error",
    [
        (httpx.ReadTimeout, GeocodingProviderTimeout),
        (httpx.ConnectError, GeocodingProviderUnavailable),
        (httpx.RemoteProtocolError, GeocodingProviderInvalidResponse),
    ],
)
async def test_transport_failure(
    failure: type[httpx.RequestError], error: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise failure("private details", request=request)

    async with httpx.AsyncClient(
        base_url="https://geo.example", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(error):
            await OpenMeteoGeocodingProvider(client).search("city", "BR", limit=10)
