from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient, Timeout

from app.api.routes.weather import router as weather_router
from app.api.schemas.health import HealthResponse
from app.application.use_cases.get_forecast import GetForecast
from app.config.settings import Settings
from app.infrastructure.weather.open_meteo import OpenMeteoProvider


def create_application(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with AsyncClient(
            base_url=str(settings.weather_provider_base_url),
            timeout=Timeout(
                connect=settings.weather_provider_connect_timeout,
                read=settings.weather_provider_read_timeout,
                write=settings.weather_provider_write_timeout,
                pool=settings.weather_provider_pool_timeout,
            ),
        ) as client:
            application.state.get_forecast = GetForecast(OpenMeteoProvider(client))
            try:
                yield
            finally:
                del application.state.get_forecast

    application = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        contact={
            "name": "Wellington Almeida",
            "email": "welli7ngton.dev@gmail.com",
        },
    )

    @application.get(
        "/health",
        tags=["health"],
        summary="Check API health",
        description="Returns a lightweight liveness response for the API process.",
        response_description="The API process is healthy and accepting requests.",
        response_model=HealthResponse,
    )
    def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    application.include_router(weather_router)
    return application


app = create_application()
