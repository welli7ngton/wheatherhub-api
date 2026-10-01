"""Translate application failures into the public HTTP contract."""

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.api.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from app.application.ports.geocoding_provider import (
    GeocodingProviderInvalidResponse,
    GeocodingProviderTimeout,
    GeocodingProviderUnavailable,
)
from app.application.ports.weather_provider import (
    WeatherProviderInvalidResponse,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)

logger = logging.getLogger(__name__)


def error_response(
    request: Request, status: int, code: ErrorCode, message: str
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code, message=message, request_id=request.state.request_id
        )
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(mode="json"),
        headers={"X-Request-ID": str(request.state.request_id)},
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.request_id = uuid4()
        try:
            response = await call_next(request)
        except Exception:
            # Catch before the outer debug/error middleware can expose a traceback.
            logger.exception(
                "Unexpected request failure request_id=%s", request.state.request_id
            )
            response = error_response(
                request, 500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
            )
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        coordinates = {"latitude", "longitude"}
        # Model validation may fail before the duplicate-check dependency runs.
        # Inspect the original query too so coordinate duplicates still win.
        coordinate_error = request.url.path == "/api/v1/weather/forecast" and (
            any(len(request.query_params.getlist(name)) > 1 for name in coordinates)
            or any(
                len(error["loc"]) >= 2
                and error["loc"][0] == "query"
                and error["loc"][1] in coordinates
                for error in exc.errors()
            )
        )
        if coordinate_error:
            return error_response(
                request,
                422,
                ErrorCode.INVALID_COORDINATES,
                "Latitude and longitude must be valid coordinates supplied once.",
            )
        return error_response(
            request, 422, ErrorCode.INVALID_QUERY, "Query parameters are invalid."
        )

    @application.exception_handler(WeatherProviderTimeout)
    async def provider_timeout(
        request: Request, exc: WeatherProviderTimeout
    ) -> JSONResponse:
        return error_response(
            request,
            504,
            ErrorCode.WEATHER_PROVIDER_TIMEOUT,
            "Weather provider timed out.",
        )

    @application.exception_handler(WeatherProviderUnavailable)
    async def provider_unavailable(
        request: Request, exc: WeatherProviderUnavailable
    ) -> JSONResponse:
        return error_response(
            request,
            503,
            ErrorCode.WEATHER_PROVIDER_UNAVAILABLE,
            "Weather provider is temporarily unavailable.",
        )

    @application.exception_handler(WeatherProviderInvalidResponse)
    async def provider_invalid_response(
        request: Request, exc: WeatherProviderInvalidResponse
    ) -> JSONResponse:
        return error_response(
            request,
            502,
            ErrorCode.WEATHER_PROVIDER_INVALID_RESPONSE,
            "Weather provider returned an invalid response.",
        )

    @application.exception_handler(GeocodingProviderTimeout)
    async def geocoding_timeout(
        request: Request, exc: GeocodingProviderTimeout
    ) -> JSONResponse:
        return error_response(
            request,
            504,
            ErrorCode.GEOCODING_PROVIDER_TIMEOUT,
            "Geocoding provider timed out.",
        )

    @application.exception_handler(GeocodingProviderUnavailable)
    async def geocoding_unavailable(
        request: Request, exc: GeocodingProviderUnavailable
    ) -> JSONResponse:
        return error_response(
            request,
            503,
            ErrorCode.GEOCODING_PROVIDER_UNAVAILABLE,
            "Geocoding provider is temporarily unavailable.",
        )

    @application.exception_handler(GeocodingProviderInvalidResponse)
    async def geocoding_invalid_response(
        request: Request, exc: GeocodingProviderInvalidResponse
    ) -> JSONResponse:
        return error_response(
            request,
            502,
            ErrorCode.GEOCODING_PROVIDER_INVALID_RESPONSE,
            "Geocoding provider returned an invalid response.",
        )
