# WeatherHub API

Backend API in Python for weather data, designed to integrate with Open-Meteo.
The project is being developed as a small production-oriented service, with a focus on clean architecture, external API integration, testing, and operational practices.

## Current Status

The API currently provides a health check endpoint:

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

The forecast use case and provider-independent internal models are implemented,
with an async provider protocol and tests using a fake provider. The Open-Meteo
adapter now validates and normalizes provider responses, with mock HTTP tests for
success and failure paths. The application lifespan now owns a configured shared
HTTP client and wires the adapter into the forecast use case. The forecast route
is available at `GET /api/v1/weather/forecast` with required `latitude` and
`longitude` and optional `forecast_days` (1–7, default 1). Unknown and repeated
parameters are rejected. Location search is available at `GET /api/v1/locations/search?name=Fortaleza&country_code=BR`
with optional `limit` (1?20, default 10). See the [location contract](docs/api/locations-v1.md)
and [ADR 004](docs/adr/004-geocoding-boundary.md).

See the [phase 3 implementation plan](docs/phase-3-implementation-plan.md) for
progress and the next implementation steps.

Phase 2 defines the [forecast v1 contract](docs/api/forecast-v1.md), including
validated request/response schemas and the error envelope. The forecast route
and error schemas are exposed in OpenAPI. Forecast errors use the documented
422/502/503/504 mappings and a safe 500 fallback. Each request receives a new
server-generated UUID in `X-Request-ID`, matching the UUID in error bodies;
client-supplied IDs are not reused. Unexpected exceptions are logged server-side
with this ID, including when debug mode is enabled. The contract uses 1-7 UTC
calendar days, hourly records and fixed units. Live provider verification remains
pending.

## Requirements

- Python 3.12 or newer
- A virtual environment is recommended

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project and development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -c constraints.txt -e ".[dev]"
```

The existing virtual environment and pip are the development workflow. Direct
dependencies live in `pyproject.toml`; `constraints.txt` pins the versions used by
local development, CI, and Docker. Constraints only apply to packages needed by
the requested installation, so development tools are not installed in the image.

Copy the configuration template (optional; defaults work without it):

```powershell
Copy-Item .env.example .env
```

`WEATHERHUB_APP_NAME` sets the API title and `WEATHERHUB_DEBUG` enables debug mode
(disabled by default). Environment variables override `.env` values. Run commands
from the repository root so that `.env` is found.

Provider configuration uses the following environment variables (also passed
through Compose):

| Variable | Default |
| --- | --- |
| `WEATHERHUB_WEATHER_PROVIDER_BASE_URL` | `https://api.open-meteo.com` |
| `WEATHERHUB_WEATHER_PROVIDER_CONNECT_TIMEOUT` | `5` seconds |
| `WEATHERHUB_WEATHER_PROVIDER_READ_TIMEOUT` | `10` seconds |
| `WEATHERHUB_WEATHER_PROVIDER_WRITE_TIMEOUT` | `5` seconds |
| `WEATHERHUB_WEATHER_PROVIDER_POOL_TIMEOUT` | `5` seconds |

The base URL must be an HTTP(S) URL. Timeouts must be positive finite numbers.
They limit connection establishment, waiting for incoming data, writing data and
waiting for a pooled connection respectively; they are not a total request
deadline. One client is created per running application lifespan and closed on
shutdown. Startup and `/health` do not contact Open-Meteo.

Routes can resolve `get_forecast_use_case` with FastAPI `Depends`; tests can
replace it through `application.dependency_overrides`. Use `TestClient` as a
context manager to run startup/shutdown. Async tests using an ASGI transport must
also run the application lifespan. See [ADR 003](docs/adr/003-provider-lifecycle.md).

When updating dependencies, update `pyproject.toml` and the corresponding pins in
`constraints.txt` together, then validate on Windows and Linux. This is a version
snapshot, not a hash-verified lockfile; build tools and the base image have their
own update lifecycle.

## Running Locally

Start the development server with auto-reload:

```powershell
task dev
```

The API will be available at <http://127.0.0.1:8000>.

FastAPI provides interactive documentation at:

- <http://127.0.0.1:8000/docs>
- <http://127.0.0.1:8000/redoc>

## Testing and Quality Checks

The project uses pytest, Ruff, mypy, and Taskipy shortcuts:

```powershell
# Run tests
task test

# Check lint rules
task lint

# Format source files
task format

# Check formatting without changing files
task format-check

# Run static type checking
task typecheck

# Run all quality checks and tests
task check
```

CI runs these checks on Python 3.12, then builds and starts the Docker service and
checks `/health`. Tests cover the health endpoint, configuration precedence and
invalid configuration. They do not call external services.

## Docker

With Docker running:

```powershell
task up
curl.exe http://127.0.0.1:8000/health
task down
```

The image runs as a non-root user and includes a health check. Compose exposes
port 8000 only on localhost and passes the settings from the environment or
`.env`. Rebuild after code changes; use `task dev` for local automatic reload.
PostgreSQL and Redis will be added when their implementation phases begin.

## Project Structure

```text
app/
  api/
    application.py       # FastAPI application factory and app instance
    dependencies.py      # API dependencies
    routes/               # HTTP route modules
    schemas/              # API response schemas
  application/
    use_cases/            # Application use cases
  config/                 # Validated environment settings

tests/
  api/                    # API tests and pytest fixtures
  unit/                   # Configuration tests

pyproject.toml            # Project metadata and tool configuration
.context/                 # Development action plan
```

## Architecture Direction

The intended request flow is:

```text
Client
  -> FastAPI route
  -> Application use case
  -> Domain service
  -> External weather provider
```

The planned integration uses Open-Meteo for weather forecasts and geocoding. Future work may add persistence, caching, resilience, observability, background processing, and production deployment.

## API Example

With the development server running, check the service with:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Location search

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/locations/search?name=Fortaleza&country_code=BR&limit=5"
```

Use coordinates from the chosen result to request a forecast. No matches return
200 with an empty `results` list. Country, region and timezone can be null.

Geocoding has its own lifespan-owned client and settings:
`WEATHERHUB_GEOCODING_PROVIDER_BASE_URL` defaults to
`https://geocoding-api.open-meteo.com`. The corresponding
`WEATHERHUB_GEOCODING_PROVIDER_CONNECT_TIMEOUT`, `READ_TIMEOUT`, `WRITE_TIMEOUT`
and `POOL_TIMEOUT` variables default to 5, 10, 5 and 5 seconds respectively
(each uses the full `WEATHERHUB_GEOCODING_PROVIDER_` prefix).
They are HTTP operation limits, not a total deadline. Compose passes all five
settings through. Tests use fake providers and HTTPX mock transport, including
invalid inputs, empty results, upstream failures and client cleanup.


Location search requires both `name` and `country_code` (for example `BR`);
the former `q` parameter is rejected. Country codes are trimmed and checked for
length two, without uppercase normalization or ISO membership validation.

`task up` builds and starts Compose, waiting for health. `task down` removes
containers, the project network and locally built images (`--rmi local`).
The current Dockerfile enables Uvicorn `--reload`, but Compose has no source
bind mount: host edits still require rebuilding with `task up`. For local
Python development, `task dev` reloads saved source changes directly.
