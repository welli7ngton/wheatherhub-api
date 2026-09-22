# 002: A small, provider-independent forecast contract

Status: accepted for the first implementation

## Context

The API needs a stable contract before connecting the external provider. Future
persistence, caching and alert evaluation also need unambiguous times and units.

## Decision

Expose hourly forecasts for 1–7 UTC calendar days (default 1). Use fixed metric
units and timezone-aware timestamps. Echo requested coordinates, since provider
grid coordinates can differ. Normalize measurements into objects per hour rather
than expose parallel provider arrays. Represent unavailable measurements as null.
Use a consistent error envelope with stable codes and a request correlation UUID.

Keep these Pydantic schemas at the HTTP boundary. Internal domain models and
provider DTOs will be introduced alongside their consumers in phase 3.

## Consequences and alternatives

Fixed UTC avoids daylight-saving ambiguity and keeps every day at 24 records.
Clients must convert to local time; a UTC day is not necessarily a local day.
Configurable units and timezone would add validation and cache key dimensions.
Defer those options until needed. Calendar days align with the provider's daily
window but include earlier hours of the current day, unlike a rolling forecast.

Separate public and provider models require mapping code, but protect clients
from provider field names and payload changes. No fake successful route is
exposed: phase 2 delivers schemas and the contract; phase 3 connects real behavior.
