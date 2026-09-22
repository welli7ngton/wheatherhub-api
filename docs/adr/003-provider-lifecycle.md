# 003: Application-owned provider client and explicit dependency wiring

Status: accepted

## Context

The forecast use case consumes an application-owned protocol. The Open-Meteo
adapter implements it and borrows an async HTTP client. Requests need connection
reuse, bounded HTTP operations and deterministic cleanup without making liveness
depend on a remote service.

## Decision

Construct one HTTPX client, adapter and use case inside each application lifespan.
The client async context manager owns cleanup, including exceptional exits.
Store only the use case on application state; remove it at shutdown so dependencies
cannot resolve a stale client. Creating the application does not open a client.
Multiple worker processes each own their own client.

Expose `get_forecast_use_case` as a FastAPI dependency. It resolves the shared use
case and supports normal dependency overrides in route tests. Application/domain
code retains no FastAPI or HTTPX dependencies. No DI framework is needed for this
small object graph.

Validate an HTTP(S) base URL and positive finite connect/read/write/pool timeout
values through Settings, with environment and Compose support. Timeout defaults
are 5/10/5/5 seconds. These operation limits do not guarantee a total request
deadline. Do not add retries or contact Open-Meteo during startup or health checks.

## Consequences and alternatives

Sharing the client enables connection reuse but requires lifecycle-aware tests.
A client per request would simplify ownership locally but repeatedly discard its
connection pool. A module-global client would complicate cleanup and application
isolation. Keeping the provider/client out of application state limits the API's
access to the use case it actually consumes.

The shared use case and adapter must remain free of mutable per-request state.
Settings fail fast on invalid configuration; provider outages do not prevent
startup. A future end-to-end deadline requires a separate policy.

References: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/).
