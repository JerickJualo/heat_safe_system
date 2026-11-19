# HeatSafe Final Project Summary

## Purpose

HeatSafe is a predictive heat-index monitoring and risk-analytics system for Surigao City, Butuan City, and Davao City. It combines historical modeled weather data, documented heat-index calculations, exploratory analysis, next-day machine learning predictions, PostgreSQL storage, and a responsive Django web interface.

## Completed capabilities

- Programmatic ERA5 historical collection through Open-Meteo.
- Asia/Manila timezone-aware hourly and daily datasets.
- NWS-style heat-index calculation and PAGASA classification.
- Historical EDA and generated charts.
- Leakage-aware next-day prediction model with chronological evaluation.
- PostgreSQL database and idempotent import process.
- Six-page web application with filters, charts, predictions, comparisons, performance metrics, reports, and CSV export.
- Production-oriented settings, validation, CSRF protection, tests, and documentation.

## Verified model result

Linear Regression was selected from the evaluated candidates. On the held-out test partition, it achieved MAE 1.2497°C, RMSE 1.6527°C, and R² 0.6045.

## Academic limitations

- Reanalysis data does not replace station observations.
- The 2026 period is partial and subject to ERA5 update delay.
- Model performance is based on the collected historical locations and feature design.
- Predictions support interpretation and planning but do not replace official public-safety advisories.
- The bundled development server is not a production deployment.

## Reproducibility

The documented clean-install and pipeline sequence in `docs/DEPLOYMENT.md` was checked against the project’s actual commands. A clean environment still requires local PostgreSQL configuration and network access to collect the generated datasets.
