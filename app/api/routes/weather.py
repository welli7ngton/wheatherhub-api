from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError

from app.api.dependencies import get_forecast_use_case
from app.api.schemas.errors import ErrorResponse
from app.api.schemas.weather import (
    ForecastLocation,
    ForecastQuery,
    ForecastResponse,
    HourlyForecast,
)
from app.application.use_cases.get_forecast import GetForecast
from app.domain.models.weather import Coordinates

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


def validate_forecast_query(
    request: Request, query: Annotated[ForecastQuery, Query()]
) -> ForecastQuery:
    """Preserve model validation and reject even identical repeated values."""
    errors = [
        {
            "type": "duplicate_query_parameter",
            "loc": ("query", name),
            "msg": "Query parameters must be supplied only once",
            "input": request.query_params.getlist(name),
        }
        for name in request.query_params
        if len(request.query_params.getlist(name)) > 1
    ]
    if errors:
        raise RequestValidationError(errors)
    return query


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    responses={
        status: {
            **({"model": ErrorResponse} if status != 200 else {}),
            "description": description,
            "headers": {
                "X-Request-ID": {
                    "description": "Server-generated request correlation UUID",
                    "schema": {"type": "string", "format": "uuid"},
                }
            },
        }
        for status, description in {
            200: "Normalized hourly forecast",
            422: "INVALID_COORDINATES or INVALID_QUERY; coordinate errors take precedence",
            502: "WEATHER_PROVIDER_INVALID_RESPONSE",
            503: "WEATHER_PROVIDER_UNAVAILABLE",
            504: "WEATHER_PROVIDER_TIMEOUT",
            500: "INTERNAL_ERROR",
        }.items()
    },
    summary="Get an hourly weather forecast",
    description=(
        "Returns 1–7 UTC calendar days with fixed metric units. "
        "Coordinates describe the requested location. Each query parameter "
        "must appear only once; unknown parameters are rejected."
    ),
)
async def get_forecast(
    query: Annotated[ForecastQuery, Depends(validate_forecast_query)],
    use_case: Annotated[GetForecast, Depends(get_forecast_use_case)],
) -> ForecastResponse:
    forecast = await use_case.execute(
        Coordinates(latitude=query.latitude, longitude=query.longitude),
        forecast_days=query.forecast_days,
    )
    return ForecastResponse(
        location=ForecastLocation(
            latitude=forecast.location.latitude,
            longitude=forecast.location.longitude,
        ),
        forecast_days=forecast.forecast_days,
        fetched_at=forecast.fetched_at,
        hourly=[
            HourlyForecast(
                time=point.time,
                temperature=point.temperature,
                humidity=point.humidity,
                precipitation_probability=point.precipitation_probability,
                wind_speed=point.wind_speed,
            )
            for point in forecast.hourly
        ],
    )
