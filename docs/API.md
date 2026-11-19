# HeatSafe API and Data Sources

Base URL during local development: `http://127.0.0.1:8000/api/`.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health/` | Database connectivity check |
| GET | `/dashboard/` | Active locations, latest complete summaries, predictions |
| GET | `/analytics/` | Complete daily summaries with optional `location`, `start_date`, `end_date`, `limit` |
| GET | `/predictions/` | Stored predictions with optional `location` and `limit` |
| POST | `/predictions/generate/` | Generate/store current predictions using the saved model; CSRF protected |
| GET | `/locations/compare/` | Same-date complete summaries; optional `date` |
| GET | `/report/` | Database counts, source attribution, methodology, limitations, evaluations |
| GET | `/model-performance/` | Model metrics and held-out actual-versus-predicted records |
| GET | `/export/daily.csv` | Streaming CSV export with optional location/date filters |

## Input validation

- Dates must use `YYYY-MM-DD`.
- Start dates cannot be after end dates.
- Unknown or inactive locations return HTTP 404.
- Analytics limits are bounded to 1–10,000.
- Prediction limits are bounded to 1–365.
- Invalid parameters return JSON errors rather than database exceptions.

## Sources and attribution

Weather source: Open-Meteo Historical Weather API, using ERA5 modeled/reanalysis data. See the [Historical Weather API documentation](https://open-meteo.com/en/docs/historical-weather-api) and [model updates documentation](https://open-meteo.com/en/docs/model-updates).

The application presents source attribution and limitations through `/api/report/` and the Reports page.
