from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError

from app.api.dependencies import get_search_location_use_case
from app.api.schemas.errors import ErrorResponse
from app.api.schemas.locations import (
    LocationQuery,
    LocationResponse,
    LocationSearchResponse,
)
from app.application.use_cases.search_location import SearchLocation

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


def validate_location_query(
    request: Request, query: Annotated[LocationQuery, Query()]
) -> LocationQuery:
    errors = [
        {
            "type": "duplicate_query_parameter",
            "loc": ("query", name),
            "msg": "Query parameters must be supplied only once",
        }
        for name in request.query_params
        if len(request.query_params.getlist(name)) > 1
    ]
    if errors:
        raise RequestValidationError(errors)
    return query


@router.get(
    "/search",
    response_model=LocationSearchResponse,
    summary="Search locations by name",
    description=(
        "Search with 2–100 characters after trimming. Returns up to 20 results "
        "in provider order, or an empty list when no matches exist. "
        "Unknown and repeated query parameters are rejected."
    ),
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
            200: "Matching locations, possibly empty",
            422: "INVALID_QUERY",
            502: "GEOCODING_PROVIDER_INVALID_RESPONSE",
            503: "GEOCODING_PROVIDER_UNAVAILABLE",
            504: "GEOCODING_PROVIDER_TIMEOUT",
            500: "INTERNAL_ERROR",
        }.items()
    },
)
async def search_locations(
    query: Annotated[LocationQuery, Depends(validate_location_query)],
    use_case: Annotated[SearchLocation, Depends(get_search_location_use_case)],
) -> LocationSearchResponse:
    locations = await use_case.execute(
        query.name, query.country_code, limit=query.limit
    )
    return LocationSearchResponse(
        results=[
            LocationResponse(
                name=item.name,
                latitude=item.latitude,
                longitude=item.longitude,
                timezone=item.timezone,
                country=item.country,
                country_code=item.country_code,
                admin1=item.admin1,
            )
            for item in locations
        ]
    )
