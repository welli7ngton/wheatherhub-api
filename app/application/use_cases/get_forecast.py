from app.application.ports.weather_provider import WeatherProvider
from app.domain.models.weather import Coordinates, Forecast


class GetForecast:
    def __init__(self, provider: WeatherProvider) -> None:
        self._provider = provider

    async def execute(
        self, coordinates: Coordinates, *, forecast_days: int = 1
    ) -> Forecast:
        """Retrieve a forecast, leaving transport error mapping to the caller."""
        if type(forecast_days) is not int or not 1 <= forecast_days <= 7:
            raise ValueError("forecast_days must be an integer from 1 through 7")
        return await self._provider.get_forecast(
            coordinates, forecast_days=forecast_days
        )
