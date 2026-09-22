from typing import Annotated

import httpx
import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient

from app.api import application as application_module
from app.api.application import create_application
from app.api.dependencies import get_forecast_use_case
from app.application.ports.weather_provider import WeatherProviderUnavailable
from app.application.use_cases.get_forecast import GetForecast
from app.config.settings import Settings
from app.domain.models.weather import Coordinates, Forecast


@pytest.fixture
def provider_clients(monkeypatch: pytest.MonkeyPatch) -> list[httpx.AsyncClient]:
    clients: list[httpx.AsyncClient] = []

    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Provider offline", request=request)

    def create_client(*, base_url: str, timeout: httpx.Timeout) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=httpx.MockTransport(unavailable),
        )
        clients.append(client)
        return client

    monkeypatch.setattr(application_module, "AsyncClient", create_client)
    return clients


@pytest.mark.asyncio
async def test_lifespan_wires_configured_client_and_cleans_up(
    provider_clients: list[httpx.AsyncClient],
) -> None:
    settings = Settings.model_validate(
        {
            "weather_provider_base_url": "https://weather.example",
            "weather_provider_connect_timeout": 1,
            "weather_provider_read_timeout": 2,
            "weather_provider_write_timeout": 3,
            "weather_provider_pool_timeout": 4,
        }
    )
    app = create_application(settings)
    request = Request({"type": "http", "app": app})
    assert provider_clients == []
    with pytest.raises(RuntimeError, match="lifespan"):
        get_forecast_use_case(request)

    async with app.router.lifespan_context(app):
        client = provider_clients[0]
        assert str(client.base_url) == "https://weather.example/"
        assert client.timeout.as_dict() == {
            "connect": 1,
            "read": 2,
            "write": 3,
            "pool": 4,
        }
        use_case = get_forecast_use_case(request)
        assert get_forecast_use_case(request) is use_case
        for _ in range(2):
            with pytest.raises(WeatherProviderUnavailable):
                await use_case.execute(Coordinates(0, 0))
        assert len(provider_clients) == 1
        assert not client.is_closed

    assert client.is_closed
    with pytest.raises(RuntimeError, match="lifespan"):
        get_forecast_use_case(request)


@pytest.mark.asyncio
async def test_lifespan_closes_client_on_error_and_can_restart(
    provider_clients: list[httpx.AsyncClient],
) -> None:
    app = create_application(Settings())
    with pytest.raises(RuntimeError, match="application failure"):
        async with app.router.lifespan_context(app):
            raise RuntimeError("application failure")
    assert provider_clients[0].is_closed
    assert not hasattr(app.state, "get_forecast")

    async with app.router.lifespan_context(app):
        assert len(provider_clients) == 2
        assert not provider_clients[1].is_closed
    assert provider_clients[1].is_closed


def test_health_does_not_call_provider(
    provider_clients: list[httpx.AsyncClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def unexpected_request(
        self: httpx.AsyncClient, request: httpx.Request, **kwargs: object
    ) -> httpx.Response:
        pytest.fail("Startup and health must not make an upstream request")

    monkeypatch.setattr(httpx.AsyncClient, "send", unexpected_request)
    with TestClient(create_application(Settings())) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert provider_clients[0].is_closed


def test_dependency_can_be_overridden(
    provider_clients: list[httpx.AsyncClient],
) -> None:
    class FakeProvider:
        async def get_forecast(
            self, coordinates: Coordinates, *, forecast_days: int
        ) -> Forecast:
            raise AssertionError("This test only resolves the dependency")

    replacement = GetForecast(FakeProvider())
    app = create_application(Settings())
    app.dependency_overrides[get_forecast_use_case] = lambda: replacement

    @app.get("/dependency-probe")
    async def probe(
        use_case: Annotated[GetForecast, Depends(get_forecast_use_case)],
    ) -> dict[str, bool]:
        return {"overridden": use_case is replacement}

    with TestClient(app) as client:
        assert client.get("/dependency-probe").json() == {"overridden": True}


@pytest.mark.asyncio
async def test_application_instances_do_not_share_clients(
    provider_clients: list[httpx.AsyncClient],
) -> None:
    first = create_application(Settings())
    second = create_application(Settings())
    async with first.router.lifespan_context(first):
        async with second.router.lifespan_context(second):
            assert first.state.get_forecast is not second.state.get_forecast
            assert len(provider_clients) == 2
        assert provider_clients[1].is_closed
        assert not provider_clients[0].is_closed
    assert provider_clients[0].is_closed
