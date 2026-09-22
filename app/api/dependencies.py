from fastapi import Request

from app.application.use_cases.get_forecast import GetForecast


def get_forecast_use_case(request: Request) -> GetForecast:
    """Resolve the application-owned use case; override this in route tests."""
    use_case = getattr(request.app.state, "get_forecast", None)
    if not isinstance(use_case, GetForecast):
        raise RuntimeError(
            "Forecast dependencies require a running application lifespan"
        )
    return use_case
