# HeatSafe Database Documentation

## Database configuration

The intended runtime database is PostgreSQL. Django can use SQLite as a local fallback when `DATABASE_BACKEND=sqlite` or when PostgreSQL credentials have not been configured, but the completed application is verified against PostgreSQL.

Required environment values are documented in `.env.example`:

```dotenv
DATABASE_BACKEND=postgresql
POSTGRES_DB=heatsafe
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-your-local-postgresql-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Schema

| Model/table | Purpose | Important keys and indexes |
|---|---|---|
| `weather_location` | Active HeatSafe locations and coordinates | Unique `slug`; ordered by name |
| `weather_weatherrecord` | Hourly weather values and quality flags | Unique `(location, recorded_at)`; location/time indexes |
| `weather_heatindexrecord` | Calculated hourly heat index and risk category | One-to-one with weather record; risk-category index |
| `weather_dailyweathersummary` | Daily and daytime aggregates | Unique `(location, local_date)`; location/date and risk indexes |
| `weather_predictionrecord` | Stored next-day model outputs | Unique `(location, target_date, model_name)`; location/date index |
| `weather_modelevaluation` | Model/split metrics | Unique `(model_name, split)` |

## Relationships

```text
Location 1 ──── many WeatherRecord 1 ──── 0/1 HeatIndexRecord
Location 1 ──── many DailyWeatherSummary
Location 1 ──── many PredictionRecord
```

## Import behavior

`python manage.py import_heatsafe_data` is idempotent. Unique constraints and conflict-aware bulk operations prevent duplicate hourly, daily, evaluation, and prediction records. The import reads the processed files and saved model artifacts; it does not collect remote data or retrain models.

## Verified PostgreSQL counts

The verified local database contained:

- 3 locations
- 259,920 hourly weather records
- 259,512 heat-index records
- 10,830 daily summaries
- 6 model-evaluation records
- 3 stored predictions

These counts are dataset-instance results and may change after a new collection or import.
