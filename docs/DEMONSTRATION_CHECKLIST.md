# HeatSafe Demonstration Checklist

## Before the demonstration

- Start PostgreSQL.
- Confirm `.env` exists and contains local credentials without displaying the password.
- Run `python manage.py check`.
- Confirm the saved model and processed data exist.
- Run `python manage.py runserver 127.0.0.1:8000`.
- Open `http://127.0.0.1:8000/`.

## Suggested 8–10 minute walkthrough

1. **Dashboard** — show the three locations, latest complete daytime heat-index cards, risk labels, trend chart, and stored next-day prediction values.
2. **Data Analytics** — select a location, apply a date range, explain complete-day filtering, risk distribution, and data-quality flags.
3. **Heat Index Prediction** — select a location and explain feature date, target date, model name, and the meaning of a next-day estimate.
4. **Location Comparison** — show the latest common complete date and compare all three locations.
5. **Model Performance** — show candidate metrics, selected Linear Regression, held-out MAE/RMSE/R², and actual-versus-predicted points.
6. **Reports & Sources** — show PostgreSQL counts, ERA5 attribution, methodology, limitations, and download a filtered CSV.
7. **Architecture** — briefly show the pipeline from Open-Meteo collection through preprocessing, ML, PostgreSQL, APIs, and frontend.

## Important statements for presentation

- Open-Meteo ERA5 values are modeled/reanalysis data, not direct station observations.
- 2026 is a partial year limited to the latest API-available timestamp.
- The model predicts the next calendar day’s maximum daytime heat index; it is not an official PAGASA warning.
- The website uses the saved model for inference; opening the site does not retrain it.
- The current verified selected-model test metrics are MAE 1.2497°C, RMSE 1.6527°C, and R² 0.6045.

## Recovery checklist

- If the dashboard shows a database error, check PostgreSQL and `.env` values.
- If data is missing after a clean clone, run the documented collection, preprocessing, training, and import sequence.
- If a prediction is unavailable, verify that the Joblib artifact and complete daily history exist.
- Do not present placeholders or empty states as real measurements.
