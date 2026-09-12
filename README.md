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

Forecast and location search use cases are planned, but their implementation is not available yet.

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
python -m pip install -e ".[dev]"
```

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
  domain/                 # Domain layer

tests/
  api/                    # API tests and pytest fixtures

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

The planned integration uses Open-Meteo for weather forecasts and geocoding. Future work may add persistence, caching, resilience, observability, background processing, and containerization.

## API Example

With the development server running, check the service with:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```
