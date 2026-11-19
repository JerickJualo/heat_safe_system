# Installation and Deployment Preparation

## Requirements

- Windows, macOS, or Linux development environment
- Python 3.14.5 used during verification
- PostgreSQL 14+ recommended for local deployment
- Internet access for Open-Meteo collection and Python package installation
- Approximately 1 GB for the project, virtual environment, and generated local data; more space is required for caches and backups

## Clean installation

From the project root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally. Never paste the PostgreSQL password into `.env.example`, and never commit `.env`.

## PostgreSQL setup

Create a database using pgAdmin or a PostgreSQL shell. For a local development user, the following is an example with placeholders:

```sql
CREATE DATABASE heatsafe;
```

Set the actual credentials in `.env`, then verify:

```powershell
pg_isready -h localhost -p 5432
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
```

## Recreate the complete application data

The raw and processed datasets are generated artifacts and may be excluded from Git. On a clean machine, run the pipeline in this order:

```powershell
.\.venv\Scripts\python.exe scripts\collect_historical_weather.py
.\.venv\Scripts\python.exe -m data_pipeline.preprocessing.run_preprocessing
.\.venv\Scripts\python.exe -m data_pipeline.analysis.run_eda
.\.venv\Scripts\python.exe scripts\train_heat_index_model.py
.\.venv\Scripts\python.exe scripts\train_multi_horizon_model.py
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_heatsafe_data
```

Collection is network-dependent and may take time. Training is explicit and is not performed when the website starts.

## Run the application

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/` and use the six-page navigation.

## Production preparation

Set `DJANGO_DEBUG=False`, provide a long random `DJANGO_SECRET_KEY`, configure `DJANGO_ALLOWED_HOSTS`, and set `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS origins actually used. Keep secure-cookie and HSTS defaults enabled when serving through HTTPS.

Before deployment:

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py migrate --noinput
```

`runserver` is for development and demonstrations only. A production deployment should use a hardened WSGI/ASGI server behind an HTTPS reverse proxy, with PostgreSQL backups and restricted database credentials. A production server is not bundled in this repository.

## Automatic Windows updates

The repository includes `scripts/run_scheduled_update.py`, which runs collection, preprocessing, next-day training, one-to-five-day training, migrations, and database import. It writes daily logs under `logs/`, prevents overlapping runs, and restores previous model artifacts if an update step fails.

Register the default daily 03:00 local-time Task Scheduler job:

```powershell
.\scripts\register_heatsafe_task.ps1
```

The task runs under the current Windows user. Windows may require permission to register the task. The machine must be awake or configured to start missed tasks when available, and PostgreSQL must be running. Verify the first run manually in Task Scheduler and inspect the generated log.

Remove the task with:

```powershell
.\scripts\unregister_heatsafe_task.ps1
```

The scheduled job is intentionally separate from Django web requests. Users continue to receive the last successful model and database state while an update is running.

## Updating datasets

When new source data is needed, rerun collection, preprocessing, and EDA. Retrain the model only if the dataset or modeling code changed. Then rerun the idempotent import command. Verify counts, date coverage, model metadata, and API health after the update.
