# HeatSafe

HeatSafe is a predictive heat-index monitoring and risk-analytics system for selected Philippine localities.

## Current status

Phase 6 is complete and awaiting approval. The project now contains the Phase 1 Django/PostgreSQL foundation, the Phase 2 programmatic ERA5 collection, Phase 3 preprocessing and exploratory analysis, Phase 4 next-day heat-index forecasting, the Phase 5 Django/PostgreSQL backend integration, and the Phase 6 database-connected frontend.

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

## Preprocessing and exploratory analysis

Run the Phase 3 preprocessing pipeline from the project root:

```powershell
.\.venv\Scripts\python.exe -m data_pipeline.preprocessing.run_preprocessing
```

This creates cleaned hourly files with NWS heat index values and PAGASA risk categories, valid-only hourly files, and a daily summary file under `data/processed/`. Incomplete trailing API rows remain visible and are flagged instead of being silently imputed. Daytime is defined as 10:00 through 16:00 Asia/Manila, inclusive.

Generate the EDA charts and findings report with:

```powershell
.\.venv\Scripts\python.exe -m data_pipeline.analysis.run_eda
```

EDA outputs are written to `data/processed/eda/`, including ten PNG charts, `eda_summary.json`, and `eda_findings.md`. Heat-index unit tests are in `tests/test_heat_index.py` and can be run with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Predictive modeling

Run the Phase 4 training pipeline from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\train_heat_index_model.py
```

The pipeline creates a leakage-aware supervised dataset from complete daily records. Each row uses current-day observations and lag/rolling history to predict the next calendar day's maximum daytime heat index. Rolling features use previous observations only. The split is chronological by target date: training, validation, then test.

The persistence baseline and Linear Regression, Random Forest Regressor, and HistGradientBoosting Regressor are evaluated with MAE, RMSE, and R². The model with the lowest validation MAE is refit on training plus validation data and evaluated once on the held-out test period.

Phase 4 outputs are written to `data/processed/ml/` and `models/phase4/`, including the engineered ML dataset, model comparison CSV, test predictions, metadata JSON, evaluation charts, and the Joblib model bundle. The reusable inference function is `predict_next_day_maximum_daytime_heat_index` in `data_pipeline/ml/inference.py`.

## Django backend and database import

Run the Phase 5 database import from the project root after PostgreSQL is configured in `.env`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_heatsafe_data
```

The import is idempotent. Unique constraints prevent duplicate weather timestamps, daily summaries, and predictions. It imports the actual processed datasets, calculated heat-index rows, model evaluation rows, and latest model predictions into PostgreSQL. A summary is written to `data/processed/ml/django_import_summary.json`.

Available JSON endpoints:

- `/api/health/` — database health check.
- `/api/dashboard/` — active locations, latest daily summaries, and latest predictions.
- `/api/analytics/?location=surigao_city&start_date=2025-01-01&end_date=2025-12-31` — complete daily analytics records.
- `/api/predictions/?location=surigao_city` — stored predictions.
- `/api/predictions/generate/` — POST endpoint to regenerate and store current predictions.
- `/api/locations/compare/?date=2026-11-13` — same-date location comparison.
- `/api/report/` — database counts, model evaluations, and predictions.

## Data attribution

Historical weather data will be collected from the Open-Meteo Historical Weather API and attributed under its applicable CC BY 4.0 terms. The project will clearly distinguish modeled/reanalysis data from direct weather-station observations.

## Website frontend

Phase 6 provides four responsive pages backed by the Django JSON endpoints:

- `/` — dashboard cards, latest complete summaries, and a historical trend chart.
- `/analytics/` — location/date filters, summary statistics, risk distribution, and daily detail.
- `/prediction/` — stored next-day model predictions and prediction history.
- `/comparison/` — shared-date location comparison and ranking.

The frontend uses a shared dark environmental-analytics design system and native SVG charts, so it does not depend on a third-party chart CDN. Values shown by the pages are loaded from PostgreSQL through `/api/`; placeholders use an em dash and are not demonstration results. The dashboard deliberately uses the latest complete daytime summary rather than an incomplete trailing day.

Run the development server with:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Then open `http://127.0.0.1:8000/`.
