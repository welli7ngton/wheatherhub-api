from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("WEATHERHUB_DEBUG=true\n", encoding="utf-8")
    monkeypatch.delenv("WEATHERHUB_DEBUG", raising=False)
    assert Settings().debug is True
    monkeypatch.setenv("WEATHERHUB_DEBUG", "false")
    assert Settings().debug is False


def test_invalid_debug_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEATHERHUB_DEBUG", "invalid")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("provider", ["WEATHER", "GEOCODING"])
@pytest.mark.parametrize("kind", ["CONNECT", "READ", "WRITE", "POOL"])
@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "invalid"])
def test_invalid_provider_timeouts(
    monkeypatch: pytest.MonkeyPatch, kind: str, value: str, provider: str
) -> None:
    monkeypatch.setenv(f"WEATHERHUB_{provider}_PROVIDER_{kind}_TIMEOUT", value)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["not-a-url", "ftp://weather.example", "https://"])
def test_invalid_provider_url(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("WEATHERHUB_WEATHER_PROVIDER_BASE_URL", value)
    with pytest.raises(ValidationError):
        Settings()


def test_provider_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "WEATHERHUB_WEATHER_PROVIDER_READ_TIMEOUT=20\n"
        "WEATHERHUB_WEATHER_PROVIDER_BASE_URL=https://dotenv.example\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEATHERHUB_WEATHER_PROVIDER_READ_TIMEOUT", "2.5")
    monkeypatch.setenv("WEATHERHUB_WEATHER_PROVIDER_BASE_URL", "https://env.example")
    settings = Settings()
    assert settings.weather_provider_read_timeout == 2.5
    assert settings.weather_provider_base_url.host == "env.example"
