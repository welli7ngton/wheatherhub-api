from fastapi import Request

from app.application.use_cases.get_forecast import GetForecast
from app.application.use_cases.search_location import SearchLocation


def get_forecast_use_case(request: Request) -> GetForecast:
    """Resolve the application-owned use case; override this in route tests."""
    use_case = getattr(request.app.state, "get_forecast", None)
    if not isinstance(use_case, GetForecast):
        raise RuntimeError(
            "Forecast dependencies require a running application lifespan"
        )
    return use_case


def get_search_location_use_case(request: Request) -> SearchLocation:
    use_case = getattr(request.app.state, "search_location", None)
    if not isinstance(use_case, SearchLocation):
        raise RuntimeError(
            "Geocoding dependencies require a running application lifespan"
        )
    return use_case
