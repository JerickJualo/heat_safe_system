# HeatSafe Build Status

## Current phase

Phase 1 — Project Initialization and Development Environment

## Completed in this phase

- Initial Django project structure created.
- Environment-based configuration prepared.
- PostgreSQL settings prepared with a SQLite development fallback.
- Initial landing page created.
- Dependency manifest and project documentation started.
- Python 3.14.5 virtual environment created at `.venv`.
- Phase 1 dependencies installed and import-verified.
- Django system checks and initial migrations completed.
- Landing page verified through a local HTTP request.
- PostgreSQL credentials configured in local `.env`.
- PostgreSQL `heatsafe` database created.
- Django migrations verified against PostgreSQL.

## Pending

- Heat-index processing and exploratory analysis.
- Machine-learning pipeline.
- PostgreSQL application models and dashboard pages.

## Verification log

- `py -3.14 -m venv .venv` — completed successfully.
- `.venv\Scripts\python.exe -m pip install -r requirements.txt` — completed successfully after allowing PyPI access.
- `.venv\Scripts\python.exe -m pip check` — `No broken requirements found.`
- `.venv\Scripts\python.exe -m django --version` — Django `5.2.19`.
- `.venv\Scripts\python.exe manage.py check` — no issues detected.
- `.venv\Scripts\python.exe manage.py migrate --noinput` — built-in migrations applied successfully using the SQLite fallback.
- `pg_isready -h localhost -p 5432` — PostgreSQL accepting connections.
- `psql -h localhost -U postgres -d postgres -w ...` — server reachable, but application credentials are not configured; PostgreSQL authentication requires a password.
- `.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload` — server started successfully.
- `Invoke-WebRequest http://127.0.0.1:8000/` — HTTP `200`; HeatSafe page content confirmed.

## Database status

The local PostgreSQL service is running and Django is configured to use the `heatsafe` PostgreSQL database. The local password remains in `.env`, which is excluded from Git.

## Phase 2 collection update

## Current active phase

Phase 2 - Historical Dataset Collection (complete; awaiting approval before Phase 3)

Phase 2 collection completed successfully using the Open-Meteo Historical Weather API and the explicit ERA5 model.

- Locations collected: Surigao City, Butuan City, and Davao City.
- Complete coverage: January 1, 2017 through December 31, 2025.
- 2026 requested through November 19, 2026, but actual non-null coverage ends at November 14, 2026 07:00 Asia/Manila.
- Raw rows per location: 86,640.
- Usable non-null rows per location: 86,504.
- Trailing null rows per location: 136, consistent with the official ERA5 five-day update delay.
- Missing timestamps in the complete 2017-2025 period: 0 per location.
- Duplicate timestamps removed: 0 per location.
- Validation status: passed for all locations.
- Collection outputs are stored under `data/raw/`.

## PostgreSQL configuration update

The previous limitation is now resolved. The local `.env` contains the PostgreSQL password, the `heatsafe` database has been created, and Django successfully connected as user `postgres` and applied all built-in migrations against PostgreSQL.
