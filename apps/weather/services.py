"""Import, retrieval, and inference services for the HeatSafe Django backend."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
from django.db import transaction
from django.utils import timezone

from data_pipeline.ml.inference import (
    load_multi_horizon_bundle,
    predict_multi_horizon_with_bundle,
    predict_with_model_bundle,
    prepare_next_day_features,
)
from data_pipeline.preprocessing.heat_index import classify_heat_index

from .models import DailyWeatherSummary, HeatIndexRecord, Location, ModelEvaluation, PredictionRecord, WeatherRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ML_DIR = PROCESSED_DIR / "ml"
MODEL_PATH = PROJECT_ROOT / "models" / "phase4" / "heat_index_next_day_model.joblib"
MULTI_HORIZON_MODEL_PATH = PROJECT_ROOT / "models" / "phase4" / "heat_index_multi_horizon_model.joblib"
LOCAL_TZ = ZoneInfo("Asia/Manila")
IMPORT_CHUNK_SIZE = 2_000

WEATHER_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
]
DAILY_FIELDS = [
    "daily_valid_hour_count",
    "daily_expected_hour_count",
    "daily_complete",
    "maximum_temperature",
    "minimum_temperature",
    "mean_temperature",
    "maximum_relative_humidity",
    "mean_relative_humidity",
    "mean_wind_speed",
    "maximum_wind_speed",
    "total_precipitation",
    "mean_cloud_cover",
    "mean_solar_radiation",
    "maximum_hourly_heat_index",
    "average_heat_index",
    "daytime_valid_hour_count",
    "daytime_expected_hour_count",
    "daytime_complete",
    "maximum_daytime_heat_index",
    "daily_risk_category",
    "data_quality_flag",
]


def _value(value):
    return None if pd.isna(value) else value


def _float_value(value):
    value = _value(value)
    return None if value is None else float(value)


def _int_value(value):
    value = _value(value)
    return None if value is None else int(value)


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _aware_datetime(value) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(LOCAL_TZ)
    else:
        timestamp = timestamp.tz_convert(LOCAL_TZ)
    return timestamp.to_pydatetime()


def _load_location_metadata() -> list[dict]:
    metadata = []
    for path in sorted(RAW_DIR.glob("*_metadata.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        metadata.append(data["location"])
    if not metadata:
        raise FileNotFoundError(f"No location metadata files found in {RAW_DIR}")
    return metadata


@transaction.atomic
def ensure_locations() -> dict[str, Location]:
    locations = {}
    for item in _load_location_metadata():
        location, _ = Location.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "province": item.get("province", ""),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "timezone": "Asia/Manila",
                "is_active": True,
            },
        )
        locations[location.slug] = location
    return locations


def _processed_hourly_paths() -> list[Path]:
    return sorted(
        path for path in PROCESSED_DIR.glob("*_city_hourly_heat_index.csv") if not path.name.startswith("all_")
    )


@transaction.atomic
def import_weather_records(locations: dict[str, Location]) -> dict[str, int]:
    counts = {}
    for path in _processed_hourly_paths():
        slug = path.name.removesuffix("_hourly_heat_index.csv")
        location = locations[slug]
        for chunk in pd.read_csv(path, chunksize=IMPORT_CHUNK_SIZE):
            records = []
            for row in chunk.to_dict(orient="records"):
                records.append(
                    WeatherRecord(
                        location=location,
                        recorded_at=_aware_datetime(row["recorded_at"]),
                        temperature_2m=_float_value(row["temperature_2m"]),
                        relative_humidity_2m=_float_value(row["relative_humidity_2m"]),
                        dew_point_2m=_float_value(row["dew_point_2m"]),
                        wind_speed_10m=_float_value(row["wind_speed_10m"]),
                        precipitation=_float_value(row["precipitation"]),
                        cloud_cover=_float_value(row["cloud_cover"]),
                        shortwave_radiation=_float_value(row["shortwave_radiation"]),
                        quality_flag=str(row["quality_flag"]),
                        is_valid_for_analysis=_bool_value(row["is_valid_for_analysis"]),
                    )
                )
            WeatherRecord.objects.bulk_create(records, batch_size=IMPORT_CHUNK_SIZE, ignore_conflicts=True)
        counts[slug] = WeatherRecord.objects.filter(location=location).count()
    return counts


@transaction.atomic
def import_heat_index_records(locations: dict[str, Location]) -> dict[str, int]:
    counts = {}
    for path in sorted(PROCESSED_DIR.glob("*_city_hourly_heat_index_valid.csv")):
        slug = path.name.removesuffix("_hourly_heat_index_valid.csv")
        location = locations[slug]
        weather_ids = {
            recorded_at: record_id
            for record_id, recorded_at in WeatherRecord.objects.filter(location=location).values_list("id", "recorded_at")
        }
        for chunk in pd.read_csv(path, chunksize=IMPORT_CHUNK_SIZE):
            records = []
            for row in chunk.to_dict(orient="records"):
                weather_id = weather_ids.get(_aware_datetime(row["recorded_at"]))
                if weather_id is None:
                    raise ValueError(f"No imported weather record for {slug} at {row['recorded_at']}")
                records.append(
                    HeatIndexRecord(
                        weather_record_id=weather_id,
                        heat_index_celsius=float(row["heat_index_celsius"]),
                        risk_category=str(row["risk_category"]),
                    )
                )
            HeatIndexRecord.objects.bulk_create(records, batch_size=IMPORT_CHUNK_SIZE, ignore_conflicts=True)
        counts[slug] = HeatIndexRecord.objects.filter(weather_record__location=location).count()
    return counts


@transaction.atomic
def import_daily_summaries(locations: dict[str, Location]) -> int:
    path = PROCESSED_DIR / "daily_heat_index.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    records = []
    for chunk in pd.read_csv(path, chunksize=IMPORT_CHUNK_SIZE):
        for row in chunk.to_dict(orient="records"):
            location = locations[str(row["location_slug"])]
            defaults = {field: row[field] for field in DAILY_FIELDS}
            for field in [
                "daily_valid_hour_count",
                "daily_expected_hour_count",
                "daytime_valid_hour_count",
                "daytime_expected_hour_count",
            ]:
                defaults[field] = _int_value(defaults[field])
            for field in [
                "maximum_temperature",
                "minimum_temperature",
                "mean_temperature",
                "maximum_relative_humidity",
                "mean_relative_humidity",
                "mean_wind_speed",
                "maximum_wind_speed",
                "total_precipitation",
                "mean_cloud_cover",
                "mean_solar_radiation",
                "maximum_hourly_heat_index",
                "average_heat_index",
                "maximum_daytime_heat_index",
            ]:
                defaults[field] = _float_value(defaults[field])
            defaults["daily_complete"] = _bool_value(defaults["daily_complete"])
            defaults["daytime_complete"] = _bool_value(defaults["daytime_complete"])
            records.append(
                DailyWeatherSummary(
                    location=location,
                    local_date=pd.Timestamp(row["local_date"]).date(),
                    **defaults,
                )
            )
    DailyWeatherSummary.objects.bulk_create(records, batch_size=IMPORT_CHUNK_SIZE, ignore_conflicts=True)
    return DailyWeatherSummary.objects.count()


@transaction.atomic
def import_model_evaluations() -> int:
    path = ML_DIR / "model_comparison.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    imported = 0
    for row in pd.read_csv(path).to_dict(orient="records"):
        ModelEvaluation.objects.update_or_create(
            model_name=str(row["model"]),
            split=str(row["split"]),
            defaults={
                "row_count": int(row["rows"]),
                "mae": float(row["mae"]),
                "rmse": float(row["rmse"]),
                "r2": float(row["r2"]),
                "metadata": {"source_file": str(path)},
            },
        )
        imported += 1
    return imported


@transaction.atomic
def generate_and_store_predictions(locations: dict[str, Location]) -> int:
    daily_path = PROCESSED_DIR / "daily_heat_index.csv"
    daily = pd.read_csv(daily_path)
    bundle = joblib.load(MODEL_PATH)
    model_name = str(bundle["model_name"])
    stored = 0
    for location in locations.values():
        history = daily[daily["location_name"] == location.name].copy()
        features = prepare_next_day_features(history)
        prediction = predict_with_model_bundle(bundle, history)
        feature_date = features["feature_date"].iloc[0].date()
        target_date = (pd.Timestamp(feature_date) + pd.Timedelta(value=1, unit="D")).date()
        PredictionRecord.objects.update_or_create(
            location=location,
            target_date=target_date,
            model_name=model_name,
            defaults={
                "feature_date": feature_date,
                "predicted_heat_index_celsius": prediction,
                "model_metadata": {
                    "model_file": str(MODEL_PATH),
                    "feature_columns": bundle["feature_columns"],
                    "forecast_horizon_days": bundle["forecast_horizon_days"],
                },
            },
        )
        stored += 1
    return stored


def generate_multi_day_forecast(location: Location, feature_date, horizon_days: int = 5) -> list[dict]:
    """Generate a bounded direct forecast from one selected complete feature date."""
    if not 1 <= horizon_days <= 5:
        raise ValueError("horizon_days must be between 1 and 5.")
    if not MULTI_HORIZON_MODEL_PATH.exists():
        raise FileNotFoundError(
            "The five-day model artifact is not available. Run scripts/train_multi_horizon_model.py first."
        )
    daily_path = PROCESSED_DIR / "daily_heat_index.csv"
    if not daily_path.exists():
        raise FileNotFoundError(daily_path)
    daily = pd.read_csv(daily_path)
    history = daily[daily["location_slug"] == location.slug].copy()
    if history.empty:
        raise ValueError(f"No processed daily history is available for {location.name}.")
    selected_date = None if feature_date is None else pd.Timestamp(feature_date).date()
    if selected_date is not None:
        history = history[pd.to_datetime(history["local_date"], errors="coerce").dt.date <= selected_date]
    bundle = load_multi_horizon_bundle(MULTI_HORIZON_MODEL_PATH)
    forecasts = predict_multi_horizon_with_bundle(bundle, history, selected_date, horizon_days)
    for forecast in forecasts:
        forecast["location"] = location.slug
        forecast["location_name"] = location.name
        forecast["risk_category"] = classify_heat_index(forecast["predicted_heat_index_celsius"])
    return forecasts


@transaction.atomic
def import_all() -> dict:
    locations = ensure_locations()
    weather_counts = import_weather_records(locations)
    heat_index_counts = import_heat_index_records(locations)
    daily_count = import_daily_summaries(locations)
    evaluation_count = import_model_evaluations()
    prediction_count = generate_and_store_predictions(locations)
    summary = {
        "locations": len(locations),
        "weather_records_by_location": weather_counts,
        "heat_index_records_by_location": heat_index_counts,
        "daily_summary_records": daily_count,
        "model_evaluation_records": evaluation_count,
        "prediction_records_generated": prediction_count,
        "database": "Django configured database",
        "generated_at": timezone.now().isoformat(),
    }
    (ML_DIR / "django_import_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
