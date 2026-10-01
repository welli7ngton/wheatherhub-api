# WeatherHub — Backend Integration Engineering Project
## Action Plan

### 1. Project Goal

Build a production-oriented backend service that integrates with the free Open-Meteo weather API and exposes a clean, stable API of its own.

The project should progressively introduce real backend engineering concerns:

- External API integration
- API design
- Domain modeling
- Separation of concerns
- Dependency inversion
- Persistence
- Caching
- Resilience
- Background processing
- Observability
- Testing
- CI/CD
- Containerization

The goal is not to build a weather UI. The goal is to use a relatively simple domain to practice professional backend engineering.

---

## 2. Target Architecture

```text
                    ┌──────────────────┐
                    │      Client      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    FastAPI API   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Application    │
                    │    Use Cases     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │      Domain      │
                    │ Weather Services │
                    └───────┬─────┬────┘
                            │     │
                 ┌──────────┘     └──────────┐
                 ▼                           ▼
        ┌────────────────┐          ┌────────────────┐
        │ Weather        │          │ Cache          │
        │ Provider       │          │ Redis          │
        │ Open-Meteo     │          └────────────────┘
        └────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ External API   │
        │ Open-Meteo     │
        └────────────────┘

                    ┌────────────────┐
                    │   PostgreSQL   │
                    └────────────────┘
```

---

# 3. Recommended Stack

| Area | Technology |
|---|---|
| Language | Python 3.12+ |
| API Framework | FastAPI |
| HTTP Client | httpx |
| Validation | Pydantic |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Cache | Redis |
| Testing | pytest |
| Linting | Ruff |
| Type Checking | mypy |
| Containers | Docker + Docker Compose |
| CI | GitHub Actions |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Weather Provider | Open-Meteo |

Do not introduce Kubernetes initially. Add infrastructure only when there is an engineering problem worth solving.

---

# 4. Phase 0 — Project Foundation

## Objectives

Create a clean repository and establish development standards.

## Tasks

- [ ] Create Git repository
- [ ] Initialize Python project
- [ ] Configure virtual environment/dependency management
- [ ] Configure Ruff
- [ ] Configure mypy
- [ ] Configure pytest
- [ ] Add `.env` configuration
- [ ] Create initial README
- [ ] Create basic FastAPI application
- [ ] Add `/health`
- [ ] Add Dockerfile
- [ ] Add Docker Compose
- [ ] Create development workflow

## Expected Result

```http
GET /health
```

returns:

```json
{
  "status": "ok"
}
```

## Engineering Concepts

- Project structure
- Configuration management
- Environment variables
- Code quality
- Type safety
- Dependency management

---

# 5. Phase 1 — Open-Meteo Integration

## Objectives

Implement the first working external API integration.

## Tasks

- [ ] Study Open-Meteo API
- [ ] Implement an HTTP client using `httpx`
- [ ] Create Open-Meteo response models
- [ ] Implement weather provider
- [ ] Handle HTTP errors
- [ ] Handle malformed responses
- [ ] Configure request timeouts
- [ ] Create weather endpoint

## Initial Endpoint

```http
GET /api/v1/weather/forecast?latitude=-3.7172&longitude=-38.5433
```

## Expected Flow

```text
HTTP Request
    ↓
FastAPI Route
    ↓
Weather Use Case
    ↓
Weather Provider
    ↓
Open-Meteo
    ↓
Domain Model
    ↓
API Response
```

## Engineering Concepts

- HTTP
- REST
- External integrations
- DTOs
- Serialization
- Error handling
- Async I/O

---

# 6. Phase 2 — Location Search

## Objectives

Allow users to search for a city instead of providing coordinates manually.

## Endpoint

```http
GET /api/v1/locations/search?name=Fortaleza&country_code=BR
```

## Tasks

- [ ] Integrate Open-Meteo Geocoding API
- [ ] Create `Location` domain model
- [ ] Normalize provider response
- [ ] Support multiple search results
- [ ] Validate query parameters
- [ ] Handle location-not-found cases
- [ ] Add tests

## Expected Flow

```text
"Fortaleza"
    ↓
Geocoding Service
    ↓
latitude / longitude / timezone
    ↓
Weather Service
    ↓
Forecast
```

---

# 7. Phase 3 — Introduce Application and Domain Layers

## Objectives

Stop coupling the API directly to the external provider.

## Target Structure

```text
app/
├── api/
│   ├── routes/
│   │   ├── weather.py
│   │   └── locations.py
│   └── dependencies.py
│
├── application/
│   └── use_cases/
│       ├── get_forecast.py
│       └── search_location.py
│
├── domain/
│   ├── models/
│   │   ├── weather.py
│   │   └── location.py
│   └── services/
│       └── weather_service.py
│
├── infrastructure/
│   ├── weather/
│   │   └── open_meteo.py
│   ├── database/
│   └── cache/
│
├── config/
│   └── settings.py
│
└── main.py
```

## Tasks

- [ ] Define provider interface/protocol
- [ ] Create `WeatherProvider`
- [ ] Implement `OpenMeteoProvider`
- [ ] Separate API schemas from domain models
- [ ] Create application use cases
- [ ] Inject dependencies
- [ ] Write unit tests against interfaces

## Engineering Concepts

- Separation of concerns
- Dependency inversion
- Dependency injection
- Interfaces
- Domain models
- Testability

---

# 8. Phase 4 — PostgreSQL Persistence

## Objectives

Persist locations and weather forecasts.

## Initial Entities

### Location

```text
id
name
country
latitude
longitude
timezone
created_at
```

### Weather Forecast

```text
id
location_id
forecast_time
temperature
humidity
precipitation_probability
wind_speed
created_at
```

## Tasks

- [ ] Configure PostgreSQL
- [ ] Create SQLAlchemy models
- [ ] Configure database session management
- [ ] Create Alembic migrations
- [ ] Persist locations
- [ ] Persist forecasts
- [ ] Add database indexes
- [ ] Implement repository layer
- [ ] Add integration tests

## Engineering Concepts

- Relational modeling
- Transactions
- Repository pattern
- Migrations
- Indexes
- Query optimization
- Database lifecycle management

---

# 9. Phase 5 — Redis Caching

## Objectives

Reduce unnecessary calls to Open-Meteo and improve response latency.

## Cache Key Example

```text
weather:{latitude}:{longitude}
```

## Example

```text
weather:-3.7172:-38.5433
TTL = 10 minutes
```

## Request Flow

```text
Request
   ↓
Redis
   │
   ├── Cache Hit ──► Return data
   │
   └── Cache Miss
           ↓
      Open-Meteo
           ↓
      Store in Redis
           ↓
        Return
```

## Tasks

- [ ] Add Redis
- [ ] Implement cache abstraction
- [ ] Add cache-aside strategy
- [ ] Configure TTL
- [ ] Serialize cached data
- [ ] Handle Redis failures gracefully
- [ ] Measure cache hit/miss rate

## Engineering Concepts

- Caching
- TTL
- Cache invalidation
- Performance
- Failure isolation

---

# 10. Phase 6 — Resilience

## Objectives

Make the service behave correctly when the external provider becomes slow or unavailable.

## Tasks

### Timeout

- [ ] Configure connection timeout
- [ ] Configure read timeout
- [ ] Define maximum request duration

### Retry

- [ ] Implement bounded retries
- [ ] Use exponential backoff
- [ ] Retry only appropriate failures
- [ ] Avoid retry storms

### Circuit Breaker

- [ ] Define failure threshold
- [ ] Implement OPEN state
- [ ] Implement HALF-OPEN state
- [ ] Implement CLOSED state

### Fallback

- [ ] Return cached forecast when provider is unavailable
- [ ] Clearly identify stale data
- [ ] Define acceptable stale-data window

## Expected Behavior

```text
Open-Meteo unavailable
        ↓
Check cache/database
        ↓
Available?
   ┌────┴────┐
  Yes        No
   ↓          ↓
Return      Controlled
stale       error
data
```

## Engineering Concepts

- Fault tolerance
- Graceful degradation
- Retry policies
- Backoff
- Circuit breakers
- Reliability

---

# 11. Phase 7 — Background Weather Updates

## Objectives

Move provider synchronization out of the request/response path.

## New Flow

```text
Scheduler
    ↓
Weather Update Job
    ↓
Weather Provider
    ↓
Normalize
    ↓
PostgreSQL
    ↓
Redis
```

## Tasks

- [ ] Introduce background worker architecture
- [ ] Create weather update job
- [ ] Define scheduling strategy
- [ ] Implement idempotent updates
- [ ] Handle failed jobs
- [ ] Add retry policy
- [ ] Record job execution status

## Concepts

- Background jobs
- Scheduling
- Workers
- Idempotency
- Eventual consistency
- Job retries

---

# 12. Phase 8 — Weather Alert Engine

## Objective

Turn the project into an actual useful backend product.

Allow users to define weather conditions.

## Example

```http
POST /api/v1/alerts
```

```json
{
  "location_id": 42,
  "condition": "precipitation_probability",
  "operator": ">",
  "value": 70
}
```

## Alert Processing

```text
Weather Update
      ↓
Alert Engine
      ↓
Evaluate Conditions
      ↓
Condition Matched?
   ┌──────┴──────┐
  No             Yes
  ↓               ↓
Done          Notification
```

## Tasks

- [ ] Create alert entity
- [ ] Create alert repository
- [ ] Create rule evaluator
- [ ] Support comparison operators
- [ ] Prevent duplicate notifications
- [ ] Track alert state
- [ ] Add notification abstraction

## Engineering Concepts

- Business rules
- State management
- Idempotency
- Event-driven thinking
- Domain services

---

# 13. Phase 9 — Observability

## Objectives

Make the system measurable and debuggable.

## Logging

Use structured logs.

Example:

```json
{
  "event": "weather_provider_request",
  "provider": "open_meteo",
  "status": 200,
  "latency_ms": 142
}
```

## Metrics

Track:

```text
http_requests_total
http_request_duration_seconds
weather_provider_requests_total
weather_provider_errors_total
weather_provider_latency
cache_hits_total
cache_misses_total
background_jobs_total
```

## Health Endpoints

```http
GET /health
GET /health/ready
```

## Tasks

- [ ] Implement structured logging
- [ ] Add request correlation IDs
- [ ] Add Prometheus metrics
- [ ] Add Grafana dashboard
- [ ] Monitor provider latency
- [ ] Monitor cache hit rate
- [ ] Monitor error rate

## Engineering Concepts

- Observability
- Metrics
- Structured logging
- Correlation IDs
- Operational debugging

---

# 14. Phase 10 — Testing Strategy

The project should have multiple testing levels.

## Unit Tests

Test:

- Domain logic
- Alert evaluation
- Weather normalization
- Cache behavior
- Retry decisions

## Integration Tests

Test:

- PostgreSQL
- Redis
- Repository implementations
- Provider integration

## API Tests

Test:

```http
GET /weather
GET /locations/search
POST /alerts
```

## Failure Tests

Simulate:

- Provider timeout
- Provider 500
- Invalid provider response
- Redis unavailable
- Database unavailable

## Target

Do not obsess over 100% coverage.

Prioritize **important business logic and failure paths**.

---

# 15. Phase 11 — CI/CD

Create a GitHub Actions pipeline.

## Pipeline

```text
Push
 ↓
Install dependencies
 ↓
Lint
 ↓
Type check
 ↓
Unit tests
 ↓
Integration tests
 ↓
Build Docker image
```

## Tasks

- [ ] Configure GitHub Actions
- [ ] Run Ruff
- [ ] Run mypy
- [ ] Run pytest
- [ ] Build Docker image
- [ ] Add test coverage reporting
- [ ] Fail builds on quality violations

---

# 16. Phase 12 — Production Deployment

Only after the previous phases are stable.

## Objectives

Deploy the service publicly.

Possible architecture:

```text
Internet
   ↓
Reverse Proxy
   ↓
FastAPI
   ├── PostgreSQL
   └── Redis
```

## Tasks

- [ ] Choose hosting provider
- [ ] Configure production environment
- [ ] Configure secrets
- [ ] Deploy API
- [ ] Deploy PostgreSQL
- [ ] Deploy Redis
- [ ] Configure HTTPS
- [ ] Configure health checks
- [ ] Configure logs
- [ ] Document deployment

Do not optimize for infrastructure complexity. The goal is to understand deployment and operations.

---

# 17. API Versioning

Use versioned endpoints from the beginning:

```text
/api/v1/weather
/api/v1/locations
/api/v1/alerts
```

Later, if breaking changes are necessary:

```text
/api/v2/weather
```

Learn to treat your API as a contract.

---

# 18. Error Handling Standard

Create a consistent error format.

Example:

```json
{
  "error": {
    "code": "WEATHER_PROVIDER_UNAVAILABLE",
    "message": "Weather data is temporarily unavailable.",
    "request_id": "abc123"
  }
}
```

Possible error codes:

```text
LOCATION_NOT_FOUND
INVALID_COORDINATES
WEATHER_PROVIDER_TIMEOUT
WEATHER_PROVIDER_UNAVAILABLE
CACHE_UNAVAILABLE
DATABASE_ERROR
ALERT_NOT_FOUND
```

Avoid exposing internal exceptions or stack traces to API consumers.

---

# 19. Documentation

The README should explain:

## Project

What WeatherHub does.

## Architecture

Include an architecture diagram.

## Stack

Explain why each major technology exists.

## Local Development

```bash
docker compose up
```

## API

Document endpoints and examples.

## Testing

```bash
pytest
```

## Quality

```bash
ruff check .
mypy .
```

## Architecture Decisions

Create an `ADR/` directory.

Example:

```text
docs/
└── adr/
    ├── 001-use-fastapi.md
    ├── 002-use-postgresql.md
    ├── 003-use-redis-cache.md
    └── 004-provider-abstraction.md
```

Each ADR should explain:

- Context
- Decision
- Alternatives
- Consequences

This is particularly valuable for practicing architecture.

---

# 20. Suggested Repository Structure

```text
weatherhub/
│
├── src/
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── config/
│   └── main.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── api/
│
├── docs/
│   └── adr/
│
├── scripts/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── README.md
└── .env.example
```

---

# 21. Definition of Done

The project is considered complete when:

- [ ] The API exposes a stable versioned contract
- [ ] Locations can be searched
- [ ] Weather forecasts can be retrieved
- [ ] Open-Meteo is isolated behind an abstraction
- [ ] Weather data is persisted
- [ ] Redis caching is implemented
- [ ] External failures are handled gracefully
- [ ] Background updates work
- [ ] Weather alerts work
- [ ] Duplicate alerts are prevented
- [ ] Logs are structured
- [ ] Metrics are available
- [ ] Health/readiness checks exist
- [ ] Unit tests exist
- [ ] Integration tests exist
- [ ] CI runs automatically
- [ ] The application runs through Docker Compose
- [ ] Production deployment is documented
- [ ] Important architecture decisions have ADRs

---

# 22. Engineering Principles to Practice

Throughout the project, deliberately ask:

### Before adding a dependency

> What problem does this solve?

### Before creating an abstraction

> What change would this abstraction protect me from?

### Before optimizing

> Do I have evidence that this is a bottleneck?

### Before adding a database query

> What is the expected access pattern?

### Before adding a retry

> Is this operation safe to repeat?

### Before adding a cache

> What is the source of truth and how stale can the data be?

### Before adding a background job

> Why does this work need to leave the request lifecycle?

### Before adding infrastructure

> What engineering problem requires it?

These questions are more important than simply learning the syntax of each technology.

---

# 23. Recommended Development Order

Follow this order rather than trying to implement everything simultaneously:

```text
1. FastAPI foundation
        ↓
2. Open-Meteo integration
        ↓
3. Location search
        ↓
4. Domain/application separation
        ↓
5. PostgreSQL
        ↓
6. Redis
        ↓
7. Resilience
        ↓
8. Background jobs
        ↓
9. Alert engine
        ↓
10. Observability
        ↓
11. Testing hardening
        ↓
12. CI/CD
        ↓
13. Deployment
```

At every stage, keep the application working and commit the changes.

---

# 24. Portfolio Positioning

Do not describe this as simply:

> "A weather API."

Position it as:

> **WeatherHub — Production-oriented weather data aggregation service built with Python and FastAPI, featuring external API abstraction, PostgreSQL persistence, Redis caching, resilient provider integration, background processing, weather alert evaluation, structured observability, automated testing, and CI/CD.**

This accurately communicates the engineering problems the project solves without pretending it is a large-scale production system.

---

# 25. Final Objective

The final project should demonstrate that you can reason about a backend system beyond writing endpoints.

You should be able to explain:

1. Why the architecture is structured this way.
2. Why the external provider is abstracted.
3. Why Redis is necessary.
4. What happens when Open-Meteo fails.
5. Why some operations are synchronous and others are asynchronous/background.
6. How data consistency is handled.
7. How duplicate processing is prevented.
8. How you monitor the system.
9. How you test failure scenarios.
10. What trade-offs you made.

The most valuable outcome is not the repository itself.

It is being able to defend the engineering decisions behind it.


## Implementation update ? 2026-09-30

The historical checklist above is not a current completion report. Forecast
layers and HTTP integration are implemented (see docs/phase-3-implementation-plan.md).
Location search is now implemented with a separate geocoding protocol, use case,
Open-Meteo adapter, endpoint, configuration and automated tests. See
`docs/api/locations-v1.md` and `docs/adr/004-geocoding-boundary.md`.
Container and live-provider verification of the forecast delivery remain pending.
Persistence is the next functional milestone after integration verification.
