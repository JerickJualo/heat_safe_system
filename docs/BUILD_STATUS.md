# HeatSafe Build Status

## Current phase

Phase 3 — Data Preprocessing, Heat Index Calculation, and EDA (complete; awaiting approval before Phase 4)

## Phase 1 completed

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

- Machine-learning pipeline.
- PostgreSQL application models and dashboard pages.

## Verification log

- `py -3.14 -m venv .venv` — completed successfully.
- `.venv\Scripts\python.exe -m pip install -r requirements.txt` — completed successfully after allowing PyPI access.
- `.venv\Scripts\python.exe -m pip check` — `No broken requirements found.`
- `.venv\Scripts\python.exe -m django --version` — Django `5.2.19`.
- `.venv\Scripts\python.exe manage.py check` — no issues detected.
- `.venv\Scripts\python.exe manage.py migrate --noinput` — initial built-in migrations applied with the SQLite fallback; PostgreSQL migrations were verified subsequently.
- `pg_isready -h localhost -p 5432` — PostgreSQL accepting connections.
- `psql -h localhost -U postgres -d postgres -w ...` — PostgreSQL server reachable; application credentials are configured in `.env`.
- `.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload` — server started successfully.
- `Invoke-WebRequest http://127.0.0.1:8000/` — HTTP `200`; HeatSafe page content confirmed.

## Database status

The local PostgreSQL service is running and Django is configured to use the `heatsafe` PostgreSQL database. The local password remains in `.env`, which is excluded from Git.

## Phase 2 collection update

## Phase 2 status

Phase 2 - Historical Dataset Collection (complete; approved before Phase 3)

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

## Phase 3 preprocessing and EDA update

## Phase 3 status

Phase 3 - Data Preprocessing, Heat Index Calculation, and EDA (complete; awaiting approval before Phase 4)

Phase 3 was implemented from the actual Phase 2 raw CSV files. No values were fabricated and no future 2026 values were filled.

- NWS heat index calculation implemented with the simple formula, Rothfusz regression, and documented low- and high-humidity adjustments.
- PAGASA heat-index categories implemented with tested boundary values: `<27` Not Hazardous, `27-32` Caution, `33-41` Extreme Caution, `42-51` Danger, and `>=52` Extreme Danger.
- Timestamps are preserved as Asia/Manila local timestamps with a `+08:00` offset.
- All three locations produced 86,640 processed hourly rows, including 86,504 valid rows and 136 flagged missing-input rows.
- Quality flags identified 136 `missing_required_input` rows per location; no invalid-range rows and no duplicate timestamps were found.
- Daily output contains 10,830 location-days, of which 10,812 have complete 24-hour and 10:00-16:00 daytime coverage.
- EDA analyzed 259,512 valid hourly records and 10,812 complete daytime daily records.
- Ten PNG charts, `eda_summary.json`, and `eda_findings.md` were generated under `data/processed/eda/`.
- Highest complete daytime heat index: 46.982 deg C in Surigao City on 2017-09-03.
- Mean daily peak daytime heat index: Surigao City 38.266 deg C, Davao City 36.621 deg C, Butuan City 36.173 deg C.
- High-risk complete daytime days: Surigao City 239, Davao City 6, Butuan City 1.

## Phase 3 verification log

- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v` — 7 tests passed.
- Phase 3 modules compiled successfully with `py_compile`.
- Processed hourly files were checked for required columns, `+0800` timestamps, duplicate timestamps, missing-input flags, and actual sample rows.
- Daily aggregation was checked for expected 24 hourly records and 7 daytime records per complete day.
- EDA ran successfully and all 10 chart files were present and non-empty.
- Phase 4 was not started.
