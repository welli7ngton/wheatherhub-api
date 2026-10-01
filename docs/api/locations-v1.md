# Location search v1

`GET /api/v1/locations/search?name=Fortaleza&country_code=BR&limit=10`

- `name`: required, trimmed, 2–100 characters after trimming.
- `country_code`: required, exactly two characters after trimming (example: `BR`).
  Passed to Open-Meteo as `countryCode`. Current validation checks length only;
  it does not validate ISO membership or convert lowercase to uppercase.
- `limit`: integer, 1–20, default 10.
- The former `q` parameter is no longer accepted; clients must send `name` and
  `country_code`. This is a breaking change to the previous v1 request.
- Unknown and repeated parameters are rejected with 422 `INVALID_QUERY`.
- Results preserve provider ranking; the API does not select a city automatically.
- English translations are requested, with the provider's native-name fallback.

```json
{
  "results": [
    {
      "name": "Fortaleza",
      "latitude": -3.71722,
      "longitude": -38.54306,
      "timezone": "America/Fortaleza",
      "country": "Brazil",
      "country_code": "BR",
      "admin1": "Ceará"
    }
  ]
}
```

Country, country code, first administrative region (`admin1`) and timezone may
be null when absent from the provider. Coordinates and name are required.
No provider identifier is exposed as an internal database identifier.
A successful search without matches returns 200 with `{"results": []}`.
Use the selected result's coordinates in `/api/v1/weather/forecast`.

Errors use the existing `error.code`, `error.message`, `error.request_id` envelope:

| Status | Code |
| --- | --- |
| 422 | INVALID_QUERY |
| 502 | GEOCODING_PROVIDER_INVALID_RESPONSE |
| 503 | GEOCODING_PROVIDER_UNAVAILABLE |
| 504 | GEOCODING_PROVIDER_TIMEOUT |
| 500 | INTERNAL_ERROR |

All responses include the server-generated `X-Request-ID`; errors repeat it in
the body. Provider details are not exposed. Rate limiting and upstream 5xx map
to unavailable; other non-200 statuses, malformed JSON, invalid records and
results exceeding the requested limit map to invalid response.

Provider documentation: https://open-meteo.com/en/docs/geocoding-api
Location data is supplied by Open-Meteo, based on GeoNames.

## Verification

Automated tests use fake providers and HTTPX mock transport, independent of
external availability. A manual request through the application on 2026-09-30
returned 503 `GEOCODING_PROVIDER_UNAVAILABLE` in the execution environment;
a successful live-provider smoke test remains pending.
