# Phase 3: Working forecast integration

Status: steps 1-4 implemented. The forecast route includes query validation,
duplicate rejection with coordinate-error precedence, explicit response mapping,
422/502/503/504 error translation, a safe logged 500 fallback, and request IDs.
Success and error responses are documented in OpenAPI and covered by API tests.
Step 5 completion, including container and live provider verification, is pending.

Step 1 adds immutable internal dataclasses, the async `WeatherProvider` protocol,
provider-independent exceptions and the constructor-injected `GetForecast` use
case. Eleven fake-provider tests cover successful retrieval, the default horizon,
invalid horizons and failure propagation. The models are typed data containers:
callers validate coordinates, and the adapter validates provider data.
The use case enforces the 1-7 day horizon for all entry points. The runtime
forecast endpoint is now registered as part of step 4.

Step 2 adds `OpenMeteoProvider` and separate Pydantic provider DTOs. Mock-transport
tests cover explicit UTC date requests, one/seven-day normalization, midnight
crossing, nulls/zeroes, malformed data and HTTP/transport failure translation.
The adapter borrows an injected client. No live provider request was used to
validate this step.

Step 3 adds validated provider URL and operation timeout settings, application
lifespan ownership of the shared client, and an overridable use-case dependency.
Tests cover configuration, resource cleanup, application isolation and provider-
independent health checks. Environment examples and Compose expose the settings.
ADR 003 records the ownership and timeout decisions. Step 4 now exposes the
forecast route with error handling and request IDs.

## Baseline progress before step 1

| Area | Evidence and status |
| --- | --- |
| Foundation | Application factory, `/health`, validated settings, pip constraints, quality commands and tests implemented. |
| Packaging and automation | Dockerfile, Compose and GitHub Actions workflow present; container execution and remote CI results were not verified in this review. |
| Forecast contract | Request, response and error schemas implemented; UTC calendar windows, fixed units and error mappings documented in `docs/api/forecast-v1.md`. |
| Runtime forecast | Not implemented. Routes, dependency module and use cases are empty placeholders. No domain models or provider adapter exist. |
| Location search and later capabilities | Not implemented. Persistence, caching, workers, alerts and metrics remain future work. |
| Validation | Ruff lint and format checks pass; strict mypy passes; all 30 tests pass on Python 3.12.9. One dependency deprecation warning remains. |
| Git state | Foundation and contract work includes modified and untracked files. The latest commit is `23d2b1e`; commit history alone understates local progress. |

The original `.context/weatherhub-action-plan.md` uses different phase numbers
and unchecked historical tasks. This plan follows the newer README and ADR 002:
phase 2 is the forecast contract, phase 3 is its implementation. This delivery
combines the original roadmap's forecast integration and the minimum application
separation needed to support it. Location search follows this delivery.

## Outcome and scope

Expose `GET /api/v1/weather/forecast` using the existing v1 contract, backed by
Open-Meteo. Preserve `/health` as a lightweight liveness endpoint.

Use this flow:

```text
Route -> GetForecast -> WeatherProvider protocol
                             ^
                       OpenMeteoProvider -> shared HTTPX client
```

The application factory wires concrete dependencies. The use case imports the
protocol and internal models, never FastAPI schemas or HTTPX types.

Do not add PostgreSQL, Redis, retries, circuit breakers, geocoding or a DI framework
in this delivery. Each introduces separate behavior to design and validate.

## Implementation sequence

### 1. Define the internal boundary

- Add `app/domain/models/weather.py` with small immutable dataclasses for
  coordinates, hourly measurements and a forecast. Use tuples for hourly records
  if the forecast is intended to be immutable.
- Add `app/application/ports/weather_provider.py` with an async `WeatherProvider`
  protocol accepting coordinates and a horizon and returning the internal forecast.
- Add provider-independent timeout, unavailable and invalid-response exceptions
  alongside that boundary.
- Implement `app/application/use_cases/get_forecast.py` through constructor
  injection and test it with a fake provider.

Why: the protocol isolates the volatile external integration and makes use-case
tests independent of the network. Dataclasses avoid tying internal data to the
public JSON representation. The cost is explicit mapping between models; keep
the models small and avoid a domain-service layer that only forwards calls.

### 2. Implement and test the Open-Meteo adapter

- Add `app/infrastructure/weather/open_meteo.py` and provider DTOs in that package.
- Inject an `httpx.AsyncClient` and a small UTC clock callable for deterministic
  date and retrieval-time tests.
- Request `temperature_2m`, `relative_humidity_2m`,
  `precipitation_probability` and `wind_speed_10m`.
- Explicitly select UTC, Celsius and km/h. Capture the UTC date immediately before
  starting the upstream request; send explicit `start_date` and inclusive
  `end_date` to anchor the requested calendar window across midnight.
- Validate status and JSON, expected units/UTC offset, required arrays, equal
  lengths, finite values, measurement ranges and exactly 24 hours per day.
  Check the first timestamp against the captured date and every following hour.
- Convert provider timestamps to aware UTC values and arrays to hourly records.
  Preserve nulls and zeroes, echo requested coordinates, and record `fetched_at`
  when the response is retrieved.
- Translate timeout to the timeout exception; connection failures, 429 and 5xx
  to unavailable; other rejected requests and malformed payloads to invalid
  response. Treat unexpected redirects as invalid responses.

Open-Meteo documents these variables, explicit date intervals and unit parameters
in its [forecast API documentation](https://open-meteo.com/en/docs). The exact
normalization and failure policy above are WeatherHub design decisions.

Why: validating before returning an internal forecast prevents upstream defects
from appearing as API serialization failures. Separate DTOs add mapping code but
keep provider changes contained. Reject broken windows rather than silently
truncating arrays with `zip` or inventing measurements.

### 3. Wire lifecycle and configuration

- Add only consumed provider settings: base URL and positive finite timeout values.
- Manage one async client per application instance through FastAPI lifespan;
  close it at shutdown and reuse it across requests.
- Construct the adapter and use case in the composition root; expose dependencies
  through `app/api/dependencies.py` and allow test overrides.
- Configure explicit HTTPX connection/read/write/pool timeouts. These are operation
  limits, not a guaranteed total request deadline; document that distinction.
- Update `.env.example` and Compose configuration for settings intended to be
  configurable in containers.

Why: a shared client supports connection reuse and explicit resource ownership.
It adds lifecycle setup to tests, but avoids creating connections for every call.
Keep startup and `/health` independent of provider availability.

### 4. Expose the HTTP contract

- Implement and register `app/api/routes/weather.py` using `ForecastQuery` and
  explicit internal-to-public response mapping.
- Reject unknown parameters; make duplicate-parameter behavior explicit in the
  contract and tests. Proposed policy: reject duplicates, with coordinate errors
  taking precedence as already specified.
- Generate a UUID per request and return `X-Request-ID` on successes and errors.
- Implement the specified 422/502/503/504 mappings and a safe 500 fallback.
  Ensure the same UUID reaches error bodies and headers, including unexpected
  errors; log unexpected exceptions server-side without leaking details.
- Document all error response models in OpenAPI. Verify validation errors use
  the existing envelope rather than FastAPI's default response.

Why: HTTP status and envelope translation belong at the API boundary. Internal
exceptions remain usable by future workers without importing HTTP concerns.
Avoid catching every exception in the adapter, which would hide programming bugs
as provider outages.

### 5. Verify and document the delivery

Add tests alongside each implementation step, using fake providers for use-case
and route tests and HTTPX mock transport for adapter tests. CI must not require
live Open-Meteo availability.

Cover:

- One-day and seven-day success, nulls, zeroes and requested versus grid coordinates.
- Missing/invalid coordinates, unknown parameters, invalid horizons and duplicates;
  invalid requests must not invoke the provider.
- Timeout, connection failure, rate limiting, upstream 5xx and rejected requests.
- Invalid JSON, missing arrays, unequal lengths, wrong units, invalid measurements,
  duplicate/missing hours and an incorrect starting date.
- A response crossing UTC midnight, with its original window preserved.
- Request-ID equality, safe unexpected errors and client cleanup on shutdown.

Run `task check`, then Docker build and `/health` smoke verification. Perform a
separate manual live forecast smoke test before declaring integration complete.
Record a short ADR for the provider boundary/client lifecycle and update README
and contract status. Reconcile the roadmap's phase labels and stale README text
that still describes containerization as future work.

## Definition of done

- The forecast endpoint returns actual normalized provider data for 1-7 UTC days.
- The existing public contract and every documented failure mapping are tested.
- Application/domain code has no imports from API schemas or infrastructure.
- Client shutdown is verified and automated tests remain network-independent.
- Quality checks and container smoke checks pass; live smoke result is recorded.
- Documentation accurately identifies implemented and deferred capabilities.

After this milestone, implement location search as a separate delivery. It can
reuse the composition and testing approach, with its own geocoding contract and
provider boundary, before persistence is introduced.
