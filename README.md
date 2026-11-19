# HeatSafe

HeatSafe is a predictive heat-index monitoring and risk-analytics system for selected Philippine localities.

## Current status

Phase 1 is establishing the Django development environment, PostgreSQL configuration, project structure, and initial landing page. Historical data collection, heat-index processing, machine learning, and dashboard features are intentionally not part of this phase.

## Development setup

1. Create and activate the local virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set the local PostgreSQL password.
4. Create a PostgreSQL database named `heatsafe`.
5. Set `DATABASE_BACKEND=postgresql` in `.env`.
6. Run `python manage.py check` and `python manage.py migrate`.
7. Start the site with `python manage.py runserver`.

If `.env` is not present, the project uses a local SQLite fallback so the initial Django shell and landing page can be verified before PostgreSQL credentials are configured. The intended application database is PostgreSQL.

## Historical data collection

Phase 2 collects hourly historical weather data programmatically from the Open-Meteo Historical Weather API. No manual CSV download is required.

Run the collector from the project root with the virtual environment active:

```powershell
.\.venv\Scripts\python.exe scripts\collect_historical_weather.py
```

The collector requests the ERA5 model only, uses Asia/Manila timestamps, requests the seven required hourly variables, retries transient failures, preserves each API JSON response, and writes raw CSV files to `data/raw/`.

The requested complete period is January 1, 2017 through December 31, 2025. The 2026 request ends at the current local date, but the collector records only the latest non-null API timestamp as the actual available end. It reports trailing null rows separately and identifies whether the gap is consistent with the official ERA5 update delay. Completed-year API responses are cached and reused on later runs; the current partial-year batch is refreshed.

Generated artifacts include:

- `data/raw/*_hourly.csv` — raw hourly data per location.
- `data/raw/api_responses/` — original API response JSON files by location and batch.
- `data/raw/*_metadata.json` — location-level metadata and validation results.
- `data/raw/collection_summary.csv` and `collection_summary.json` — collection coverage and counts.
- `data/raw/validation_report.json` — validation report.

Open-Meteo data is modeled/reanalysis data and must not be described as direct local weather-station observations. Cite the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), its [model availability documentation](https://open-meteo.com/en/docs/model-updates), and the underlying ERA5 data sources when presenting the data.

## Data attribution

Historical weather data will be collected from the Open-Meteo Historical Weather API and attributed under its applicable CC BY 4.0 terms. The project will clearly distinguish modeled/reanalysis data from direct weather-station observations.
