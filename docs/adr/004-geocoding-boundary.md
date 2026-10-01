# ADR 004: Separate geocoding boundary

Status: accepted

## Context

City search is needed before clients can request forecasts by coordinates.
Geocoding and forecasting have different payloads, hosts and failure contexts.

## Decision

Use `SearchLocation -> GeocodingProvider -> OpenMeteoGeocodingProvider` with
immutable internal locations and explicit public response mapping. Keep query
and limit rules in the use case for future non-HTTP callers; HTTP schemas reject
invalid requests before provider invocation.

Own a separate configured HTTPX client in application lifespan. Both clients
reuse connections and close at shutdown. Startup and health perform no network
requests. Geocoding errors have their own HTTP error codes.

Return an empty collection for no matches, preserve ranking and let callers
choose among ambiguous places. Request English results initially. Optional
metadata is nullable; do not fabricate a timezone or country. Reject malformed
records rather than silently returning partial results. Cap results at 20 and
trim query whitespace before applying the 2–100 character limit.

## Alternatives and consequences

Extending WeatherProvider would combine independent capabilities and force
forecast fakes to model geocoding. A generic provider base class would introduce
an abstraction without shared application behavior. Separate ports add some
mapping and wiring but allow independent tests and future provider replacement.

Two clients consume separate connection pools, in exchange for independent
hosts, timeout configuration and lifecycle clarity. No DI framework is needed.
Provider DTOs stay beside this small adapter until their size warrants a module.
Timezone strings are carried as metadata, not used for forecast conversion;
forecasts continue to use UTC. Persistence and stable internal location IDs
remain separate future decisions.


## Country-filter update

Search now requires `name` and `country_code`; the adapter forwards the country
as `countryCode`. Restricting the search to a country reduces cross-country
ambiguity but requires callers to supply a country in every request. The former
`q` contract is no longer accepted. Name and country are trimmed; country
validation currently checks only a length of two, without case normalization
or ISO membership validation.
