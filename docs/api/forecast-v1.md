# Forecast API v1 contract

Status: the forecast route, query validation and success response are implemented
and exposed in OpenAPI. Custom error envelopes, provider error HTTP mappings and
request IDs remain pending. Validation currently returns FastAPI's default 422
response. Live provider verification remains pending.

## Request

`GET /api/v1/weather/forecast?latitude=-3.7172&longitude=-38.5433&forecast_days=1`

| Query parameter | Required | Rule |
| --- | --- | --- |
| latitude | yes | Finite number from -90 through 90 |
| longitude | yes | Finite number from -180 through 180 |
| forecast_days | no | Integer from 1 through 7; default 1 |

Unknown query parameters are rejected. NaN, infinity, missing coordinates and
out-of-range values are invalid. Query values are parsed from HTTP strings.
Repeated query parameters are rejected with HTTP 422, including identical values;
clients must send each parameter once. The planned error code is
`INVALID_COORDINATES` for repeated coordinates and `INVALID_QUERY` for other
repeated parameters, with coordinate errors taking precedence.

## Success: 200

The response contains `location` (requested latitude and longitude), `timezone`
(`UTC`), `forecast_days`, `fetched_at`, `units`, and `hourly`.

`hourly` contains exactly 24 records per day, sorted with consecutive hourly
timestamps, beginning at midnight UTC on the first day requested from the
provider. That day is the current UTC date when the upstream request is started.
These are calendar days, not a rolling window of the next 24 hours; earlier hours
of today are included. A request crossing midnight retains its original window.

Every timestamp is timezone-aware and serialized in UTC. `fetched_at` is the time
WeatherHub retrieved the response, not the time the weather model was issued.
The adapter must check that the returned window matches the requested date.

The following is an abbreviated example (a real one-day response has 24 entries):

```json
{
  "location": {"latitude": -3.7172, "longitude": -38.5433},
  "timezone": "UTC",
  "forecast_days": 1,
  "fetched_at": "2026-09-16T10:05:00Z",
  "units": {
    "temperature": "celsius",
    "humidity": "percent",
    "precipitation_probability": "percent",
    "wind_speed": "km/h"
  },
  "hourly": [
    {
      "time": "2026-09-16T00:00:00Z",
      "temperature": 27.4,
      "humidity": 80,
      "precipitation_probability": null,
      "wind_speed": 14.2
    }
  ]
}
```

Temperature is at 2 m, relative humidity at 2 m, and wind speed at 10 m.
Percentages are in [0, 100], wind speed is nonnegative, and all numbers are finite.
Each measurement key is required but may be `null` when its value is unavailable.
Zero is a measurement, not a substitute for missing data. Missing arrays, missing
hours, mismatched lengths or an invalid upstream payload are provider errors.
Coordinates describe the requested location, not the provider's grid resolution.

## Errors

All forecast errors will use this envelope, including request validation errors:

```json
{
  "error": {
    "code": "INVALID_COORDINATES",
    "message": "Latitude and longitude must be valid coordinates.",
    "request_id": "72174a7b-a22b-4269-8674-8ce1a1fdf835"
  }
}
```

| HTTP | Code | Condition |
| --- | --- | --- |
| 422 | INVALID_COORDINATES | Missing, malformed or out-of-range coordinate |
| 422 | INVALID_QUERY | Invalid horizon or unknown parameter |
| 504 | WEATHER_PROVIDER_TIMEOUT | Upstream timeout |
| 503 | WEATHER_PROVIDER_UNAVAILABLE | Connection failure, rate limit or upstream service failure |
| 502 | WEATHER_PROVIDER_INVALID_RESPONSE | Invalid upstream content or rejected adapter request |
| 500 | INTERNAL_ERROR | Unexpected application error |

When multiple query errors occur, coordinate errors take precedence. Messages
are descriptive and may evolve; clients branch on `code`. Generate a UUID per
request and return it as `X-Request-ID` on both success and error responses, with
the same UUID in error bodies. Do not expose upstream payloads, internal exception
messages or stack traces. These mappings are requirements for phase 3, not
implemented exception handlers in this delivery.

## Provider boundary

The public schemas contain no Open-Meteo response models. Internal models and an
adapter translate provider arrays into hourly records. The route explicitly maps
internal forecasts to public schemas; the use case does not depend on HTTP schemas.

Reference: [Open-Meteo forecast documentation](https://open-meteo.com/en/docs).
