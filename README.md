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

## Data attribution

Historical weather data will be collected from the Open-Meteo Historical Weather API and attributed under its applicable CC BY 4.0 terms. The project will clearly distinguish modeled/reanalysis data from direct weather-station observations.
