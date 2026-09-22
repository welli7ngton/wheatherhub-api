from typing import Annotated

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

TimeoutSeconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WEATHERHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WeatherHub API"
    debug: bool = False
    weather_provider_base_url: AnyHttpUrl = AnyHttpUrl("https://api.open-meteo.com")
    weather_provider_connect_timeout: TimeoutSeconds = 5.0
    weather_provider_read_timeout: TimeoutSeconds = 10.0
    weather_provider_write_timeout: TimeoutSeconds = 5.0
    weather_provider_pool_timeout: TimeoutSeconds = 5.0
