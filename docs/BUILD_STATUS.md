# HeatSafe Build Status

## Current phase

Phase 9 — Documentation, Deployment Preparation, and Final Delivery (complete; awaiting approval)

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

- No further phase work is started; awaiting approval of Phase 9.

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
- Phase 4 had not started at the time of the Phase 3 verification.

## Phase 4 predictive modeling update

Phase 4 - Predictive Machine Learning Development (complete; awaiting approval before Phase 5)

- Built 10,788 supervised next-day forecast rows from complete daily observations across the three locations.
- Target: next calendar day's maximum daytime heat index in Celsius.
- Added current-day weather features, one- and two-day heat-index lags, previous-only 3-day and 7-day rolling means, location encoding, and seasonal sine/cosine features.
- Chronological split by target date: training 7,551 rows, validation 1,617 rows, and test 1,620 rows.
- Evaluated persistence baseline, Linear Regression, Random Forest Regressor, and HistGradientBoosting Regressor.
- Selected Linear Regression by lowest validation MAE of 1.2117 deg C.
- Held-out test performance after refitting on training plus validation: MAE 1.2497 deg C, RMSE 1.6527 deg C, R2 0.6045.
- Saved the Joblib model bundle, metadata, model comparison report, test predictions, and evaluation charts.
- Verified saved-model loading and inference on actual recent valid history for Surigao City, Butuan City, and Davao City.
- Phase 5 had not started at the time of the Phase 4 verification.

## Phase 5 Django backend and PostgreSQL update

Phase 5 - Django Backend and PostgreSQL Integration (complete; approved before Phase 6)

- Added the `apps.weather` Django application and PostgreSQL-backed models for locations, hourly weather, heat-index records, daily summaries, predictions, and model evaluations.
- Applied migration `apps.weather.0001_initial` successfully.
- Added an idempotent `import_heatsafe_data` management command with chunked bulk imports and unique constraints.
- Imported actual records into PostgreSQL: 3 locations, 259,920 hourly weather records, 259,512 heat-index records, 10,830 daily summaries, 6 model evaluation records, and 3 prediction records.
- Connected Django prediction services to the saved Phase 4 Joblib model and stored current predictions for all three locations.
- Added dashboard, analytics, prediction, prediction-generation, location-comparison, report, and health endpoints under `/api/`.
- Added admin registrations for all backend models.

## Phase 5 verification log

- `.venv\Scripts\python.exe manage.py check` — no issues detected.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` — no changes detected.
- `.venv\Scripts\python.exe manage.py migrate --check` — no unapplied migrations.
- `.venv\Scripts\python.exe manage.py test apps.weather -v 1` — 5 tests passed against a temporary PostgreSQL test database.
- Idempotent import rerun — record counts remained unchanged.
- Duplicate checks — zero duplicate weather, daily-summary, and prediction key groups.
- Health endpoint returned HTTP 200 with database status true.
- API endpoint tests passed for dashboard, analytics validation, predictions, location comparison, and report retrieval.
- Phase 6 frontend implementation followed after Phase 5 approval.

## Phase 6 website frontend update

Phase 6 - Website Frontend Development (complete; awaiting approval before Phase 7)

- Added a shared responsive application shell with HeatSafe navigation, status indicators, accessible skip navigation, and mobile menu behavior.
- Added database-connected Dashboard, Data Analytics, Heat Index Prediction, and Location Comparison pages.
- Added reusable dark navy environmental-analytics styling with orange/red risk indicators, responsive grids, tables, loading states, error states, and native SVG charts.
- Connected location filters, date filters, risk summaries, historical trends, comparison ranking, and stored prediction outputs to the Phase 5 JSON endpoints.
- Added frontend route tests covering all four pages.
- No demonstration metrics are embedded as result values; the UI renders API data or an em dash when data is unavailable.

## Phase 6 verification log

- `.venv\Scripts\python.exe manage.py check` — no issues detected.
- `.venv\Scripts\python.exe manage.py test apps.core -v 2` — 1 frontend route test passed.
- `.venv\Scripts\python.exe manage.py test apps.weather -v 2` — 5 backend API tests passed.
- Python modules compiled successfully with `compileall`.
- Fresh development server returned HTTP 200 for `/`, `/analytics/`, `/prediction/`, and `/comparison/`.
- `/api/health/` returned `{"status": "ok", "database": true}`.
- Actual dashboard response returned the three imported locations and latest complete summary date `2026-11-13`.
- Actual filtered analytics request for `davao_city`, `2025-01-01` through `2025-01-10`, returned five records with requested location and dates.
- Actual comparison request returned the latest common complete date `2026-11-13` for all three locations.
- Actual prediction request for `butuan_city` returned its stored model output for target date `2026-11-14`.
- Native SVG chart assets and the frontend JavaScript loaded with HTTP 200.
- Automated computer-use visual inspection was attempted but the Windows UI helper timed out twice; route/API verification completed successfully, but no visual screenshot claim is made.

## Phase 7 model performance and reports update

Phase 7 - Model Performance, Reports, and Final Website Features (complete; awaiting approval)

- Added `/performance/` with real PostgreSQL model-evaluation metrics and actual-versus-predicted visualization data sourced from the held-out test artifact.
- Added `/reports/` with real database counts, Open-Meteo/ERA5 attribution, methodology, limitations, and CSV export controls.
- Added `/api/model-performance/` and `/api/export/daily.csv`.
- Added filtered daily-summary CSV export with location and date validation.
- Added six-page navigation and frontend route coverage.
- PDF export was not added because no existing PDF dependency was available with a reliable verification path; CSV export is the supported report export.

## Phase 7 verification log

- `.venv\Scripts\python.exe manage.py check` — no issues detected.
- `node --check static\js\app.js` — passed.
- `.venv\Scripts\python.exe manage.py test apps.core apps.weather -v 2 --keepdb` — 7 tests passed.
- Fresh development server returned HTTP 200 for `/`, `/analytics/`, `/prediction/`, `/comparison/`, `/performance/`, and `/reports/`.
- `/api/model-performance/` returned the actual selected model `linear_regression`, six evaluation records, and 1,620 held-out prediction rows.
- The selected test metrics matched the Phase 4 artifact: MAE 1.2497°C, RMSE 1.6527°C, and R² 0.6045.
- `/api/report/` returned PostgreSQL-backed counts: 3 locations, 259,920 weather records, 259,512 heat-index records, 10,830 daily summaries, and 3 stored predictions.
- Filtered CSV export for Davao City, 2025-01-01 through 2025-01-02 returned a header plus the two expected daily records.

## Phase 8 testing, security, and optimization update

Phase 8 - Testing, Security, Optimization, and Bug Fixes (complete; awaiting approval)

- Added production-safe settings validation: production requires a long secret key and non-empty allowed hosts; secure cookies, HSTS, content-type protection, referrer policy, and frame protection are configured.
- Added explicit CSRF trusted-origin configuration while retaining Django CSRF middleware protection.
- Added recursive ignore rules for nested Joblib/Pickle model artifacts and confirmed `.env` remains ignored.
- Removed unused Plotly from `requirements.txt` and the virtual environment; `pip check` remains clean.
- Optimized stored prediction generation to load the model bundle once per import operation.
- Reduced the location-comparison endpoint from an existence query plus fetch to one materialized query.
- Added validation and CSRF tests for API error handling and protected POST behavior.

## Phase 8 verification log

- `manage.py check` — passed with no issues.
- `manage.py check --deploy` with production-style environment variables — passed with no issues.
- Python unit tests — 12 passed, covering cleaning, timezone/coverage flags, daily aggregation, heat-index formulas, PAGASA boundaries, ML leakage, chronological splits, and rolling features.
- Django backend/frontend tests — 8 passed, including API, database, frontend routes, CSV export, validation, and CSRF checks.
- `pip check` — no broken requirements.
- Python `compileall` — passed.
- `node --check static\js\app.js` — passed.
- `makemigrations --check --dry-run` — no changes detected.
- `migrate --check` — no unapplied migrations.
- Import verification for Django, NumPy, pandas, requests, psycopg, scikit-learn, Matplotlib, Seaborn, Joblib, and python-dotenv — passed.
- Responsive CSS audit confirmed mobile breakpoints and mobile sidebar behavior are present. Automated visual browser inspection was not available in this run, so no screenshot-based claim is made.

## Phase 4 verification log

- `.venv\Scripts\python.exe scripts\train_heat_index_model.py` — completed successfully.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v` — 10 tests passed.
- Feature leakage checks passed: target and target date excluded from model inputs; rolling features use shifted observations.
- Chronological split check passed with non-overlapping target-date ranges.
- Saved Joblib artifact loaded successfully.
- Actual recent-history inference returned numerical predictions for all three locations.

## Phase 9 completed

- Completed the README with installation, environment, data, ML, backend, frontend, reporting, testing, and demonstration instructions.
- Added `docs/DEPLOYMENT.md` with clean-environment setup, PostgreSQL configuration, pipeline execution, update procedures, and production preparation notes.
- Added `docs/DATA_METHODOLOGY.md` documenting Open-Meteo ERA5 collection, Asia/Manila timestamps, 2017–2025 complete coverage, 2026 partial coverage, preprocessing, heat-index calculation, and data limitations.
- Added `docs/ML_METHODOLOGY.md` documenting the prediction target, feature availability, leakage controls, chronological splits, candidate models, evaluation metrics, and inference artifact.
- Added `docs/DATABASE.md` documenting the PostgreSQL schema, relationships, import command, idempotency, and verified record counts.
- Added `docs/API.md` documenting the public JSON endpoints, filters, validation behavior, and data attribution.
- Added `docs/ARCHITECTURE.md` with the system architecture diagram and repository data-flow boundaries.
- Added `docs/TESTING_REPORT.md` with the final automated verification results and known visual-testing limitation.
- Added `docs/DEMONSTRATION_CHECKLIST.md` with a concise academic presentation walkthrough and recovery notes.
- Added `docs/FINAL_SUMMARY.md` with the project purpose, completed capabilities, model result, reproducibility notes, and limitations.
- The documented setup and execution entry points were checked against the working `.venv`, Django project, PostgreSQL database, data artifacts, model artifact, and current test suite. The full remote collection and model retraining sequence was not rerun during documentation work because it would overwrite the already verified generated artifacts; the exact commands remain documented for a deliberate refresh.

## Post-Phase 9 prediction enhancement

- Added direct multi-horizon model training for horizons 1 through 5 with `scripts/train_multi_horizon_model.py`.
- Saved `models/phase4/heat_index_multi_horizon_model.joblib` and `data/processed/ml/multi_horizon_model_metadata.json`.
- Added `/api/predictions/forecast/` with bounded horizon validation and complete-feature-date validation.
- Updated the Prediction page with location and feature-date controls and a five-day forecast table.
- Verified the real Surigao City feature date `2026-11-13` returns five numerical predictions for `2026-11-14` through `2026-11-18`.
- Five-day direct-model held-out test MAE increases from 1.2497°C at horizon 1 to 1.5380°C at horizon 5; this expected degradation is documented for transparent interpretation.

## Automatic update enhancement

- Added `scripts/run_scheduled_update.py` for collection, preprocessing, model retraining, migrations, and database import.
- Added single-instance locking, daily log files, and model-artifact rollback on failed updates.
- Added Windows Task Scheduler registration and removal scripts.
- Registered `HeatSafe-Daily-Data-Update` under the current Windows user for daily execution at 03:00 local time. The task is currently `Ready`; its first scheduled run is the next 03:00 occurrence.
- Made the database import operation atomic so a failed import does not leave a partial refresh.
