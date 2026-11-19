"""JSON endpoints for dashboard, analytics, comparisons, reports, exports, and predictions."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from django.db import connection
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST

from .models import DailyWeatherSummary, HeatIndexRecord, Location, ModelEvaluation, PredictionRecord, WeatherRecord
from .services import ensure_locations, generate_and_store_predictions


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _parse_date(value: str | None, field_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


def _get_location(slug: str | None) -> Location | None:
    if not slug:
        return None
    return Location.objects.filter(slug=slug, is_active=True).first()


def _daily_payload(summary: DailyWeatherSummary) -> dict:
    return {
        "location": summary.location.slug,
        "location_name": summary.location.name,
        "date": summary.local_date.isoformat(),
        "maximum_daytime_heat_index": summary.maximum_daytime_heat_index,
        "maximum_hourly_heat_index": summary.maximum_hourly_heat_index,
        "average_heat_index": summary.average_heat_index,
        "daily_risk_category": summary.daily_risk_category,
        "maximum_temperature": summary.maximum_temperature,
        "mean_relative_humidity": summary.mean_relative_humidity,
        "total_precipitation": summary.total_precipitation,
        "daytime_valid_hour_count": summary.daytime_valid_hour_count,
        "daytime_expected_hour_count": summary.daytime_expected_hour_count,
        "daytime_complete": summary.daytime_complete,
        "data_quality_flag": summary.data_quality_flag,
    }


@require_GET
def dashboard_data(request):
    locations = Location.objects.filter(is_active=True)
    payload = []
    for location in locations:
        latest = (
            location.daily_summaries
            .filter(daytime_complete=True)
            .order_by("-local_date")
            .first()
        )
        prediction = location.predictions.order_by("-target_date").first()
        payload.append(
            {
                "slug": location.slug,
                "name": location.name,
                "province": location.province,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
                "latest_summary": _daily_payload(latest) if latest else None,
                "latest_prediction": (
                    {
                        "target_date": prediction.target_date.isoformat(),
                        "predicted_heat_index_celsius": prediction.predicted_heat_index_celsius,
                        "model_name": prediction.model_name,
                    }
                    if prediction
                    else None
                ),
            }
        )
    return JsonResponse({"locations": payload})


@require_GET
def analytics_data(request):
    try:
        start_date = _parse_date(request.GET.get("start_date"), "start_date")
        end_date = _parse_date(request.GET.get("end_date"), "end_date")
    except ValueError as exc:
        return _error(str(exc))
    if start_date and end_date and start_date > end_date:
        return _error("start_date cannot be after end_date.")
    location = _get_location(request.GET.get("location"))
    if request.GET.get("location") and location is None:
        return _error("Unknown or inactive location.", 404)
    try:
        limit = min(max(int(request.GET.get("limit", "365")), 1), 10_000)
    except ValueError:
        return _error("limit must be an integer.")
    summaries = DailyWeatherSummary.objects.select_related("location").filter(daytime_complete=True)
    if location:
        summaries = summaries.filter(location=location)
    if start_date:
        summaries = summaries.filter(local_date__gte=start_date)
    if end_date:
        summaries = summaries.filter(local_date__lte=end_date)
    summaries = summaries.order_by("local_date", "location")[:limit]
    return JsonResponse({"count": len(summaries), "records": [_daily_payload(item) for item in summaries]})


@require_GET
def prediction_data(request):
    location = _get_location(request.GET.get("location"))
    if request.GET.get("location") and location is None:
        return _error("Unknown or inactive location.", 404)
    try:
        limit = min(max(int(request.GET.get("limit", "30")), 1), 365)
    except ValueError:
        return _error("limit must be an integer.")
    predictions = PredictionRecord.objects.select_related("location")
    if location:
        predictions = predictions.filter(location=location)
    records = [
        {
            "location": item.location.slug,
            "location_name": item.location.name,
            "feature_date": item.feature_date.isoformat(),
            "target_date": item.target_date.isoformat(),
            "model_name": item.model_name,
            "predicted_heat_index_celsius": item.predicted_heat_index_celsius,
            "generated_at": item.generated_at.isoformat(),
        }
        for item in predictions.order_by("-target_date", "location")[:limit]
    ]
    return JsonResponse({"count": len(records), "records": records})


@require_POST
def generate_predictions(request):
    try:
        locations = ensure_locations()
        generated = generate_and_store_predictions(locations)
    except Exception as exc:
        return _error(f"Prediction generation failed: {exc}", 500)
    return JsonResponse({"generated": generated}, status=201)


@require_GET
def location_comparison(request):
    try:
        requested_date = _parse_date(request.GET.get("date"), "date")
    except ValueError as exc:
        return _error(str(exc))
    if requested_date is None:
        requested_date = (
            DailyWeatherSummary.objects.filter(daytime_complete=True).order_by("-local_date").values_list("local_date", flat=True).first()
        )
    if requested_date is None:
        return _error("No complete daily summaries are available.", 404)
    summaries = DailyWeatherSummary.objects.select_related("location").filter(
        local_date=requested_date, daytime_complete=True, location__is_active=True
    ).order_by("location__name")
    summaries = list(summaries)
    if not summaries:
        return _error("No complete daily summaries exist for the requested date.", 404)
    return JsonResponse({"date": requested_date.isoformat(), "locations": [_daily_payload(item) for item in summaries]})


@require_GET
def report_data(request):
    evaluations = list(
        ModelEvaluation.objects.values("model_name", "split", "row_count", "mae", "rmse", "r2")
    )
    predictions = PredictionRecord.objects.select_related("location").order_by("location__name")
    return JsonResponse(
        {
            "database": {"vendor": connection.vendor, "configured": True},
            "data_source": {
                "provider": "Open-Meteo Historical Weather API",
                "endpoint": "https://archive-api.open-meteo.com/v1/archive",
                "weather_model": "ERA5",
                "resolution": "Hourly",
                "timezone": "Asia/Manila",
                "coverage": "2017-01-01 through the latest non-null 2026 timestamp returned by the API",
                "attribution": "Open-Meteo historical reanalysis data; see the Open-Meteo documentation and underlying ERA5 sources.",
            },
            "methodology": {
                "heat_index": "National Weather Service Rothfusz regression with documented adjustments.",
                "classification": "PAGASA heat-index categories.",
                "prediction_target": "Next calendar day maximum daytime heat index.",
                "daytime_window": "10:00 through 16:00 Asia/Manila, inclusive.",
                "split": "Chronological train, validation, and test partitions.",
            },
            "limitations": [
                "Open-Meteo ERA5 values are modeled reanalysis data, not direct station observations.",
                "2026 is a partial year and remains subject to the source model update delay.",
                "Predictions are decision-support estimates and should not replace official PAGASA advisories.",
            ],
            "counts": {
                "locations": Location.objects.filter(is_active=True).count(),
                "weather_records": WeatherRecord.objects.count(),
                "heat_index_records": HeatIndexRecord.objects.count(),
                "daily_summaries": DailyWeatherSummary.objects.count(),
                "predictions": PredictionRecord.objects.count(),
            },
            "model_evaluations": evaluations,
            "latest_predictions": [
                {
                    "location": item.location.slug,
                    "target_date": item.target_date.isoformat(),
                    "predicted_heat_index_celsius": item.predicted_heat_index_celsius,
                    "model_name": item.model_name,
                }
                for item in predictions
            ],
        }
    )


def _model_prediction_rows() -> list[dict]:
    path = Path(settings.BASE_DIR) / "data" / "processed" / "ml" / "selected_model_test_predictions.csv"
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            try:
                rows.append(
                    {
                        "target_date": row["target_date"],
                        "location_name": row["location_name"],
                        "actual": float(row["actual"]),
                        "predicted": float(row["predicted"]),
                        "absolute_error": float(row["absolute_error"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
    return rows


@require_GET
def model_performance_data(request):
    evaluations = list(
        ModelEvaluation.objects.values(
            "model_name", "split", "row_count", "mae", "rmse", "r2"
        )
    )
    predictions = _model_prediction_rows()
    return JsonResponse(
        {
            "selected_model": "linear_regression",
            "test_prediction_count": len(predictions),
            "metrics": evaluations,
            "predictions": predictions,
            "visualization": {
                "x": "actual",
                "y": "predicted",
                "unit": "degrees Celsius",
                "source": "selected_model_test_predictions.csv",
            },
        }
    )


def _filtered_daily_summaries(request):
    try:
        start_date = _parse_date(request.GET.get("start_date"), "start_date")
        end_date = _parse_date(request.GET.get("end_date"), "end_date")
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")
    location = _get_location(request.GET.get("location"))
    if request.GET.get("location") and location is None:
        raise LookupError("Unknown or inactive location.")
    summaries = DailyWeatherSummary.objects.select_related("location").filter(daytime_complete=True)
    if location:
        summaries = summaries.filter(location=location)
    if start_date:
        summaries = summaries.filter(local_date__gte=start_date)
    if end_date:
        summaries = summaries.filter(local_date__lte=end_date)
    return summaries.order_by("local_date", "location")


class _Echo:
    def write(self, value):
        return value


@require_GET
def export_daily_csv(request):
    try:
        summaries = _filtered_daily_summaries(request)
    except ValueError as exc:
        return _error(str(exc))
    except LookupError as exc:
        return _error(str(exc), 404)
    field_names = [
        "location", "location_name", "date", "maximum_daytime_heat_index",
        "maximum_hourly_heat_index", "average_heat_index", "daily_risk_category",
        "maximum_temperature", "mean_relative_humidity", "total_precipitation",
        "daytime_valid_hour_count", "daytime_expected_hour_count", "daytime_complete",
        "data_quality_flag",
    ]

    def rows():
        writer = csv.DictWriter(_Echo(), fieldnames=field_names)
        yield writer.writeheader()
        for summary in summaries.iterator(chunk_size=1000):
            yield writer.writerow(_daily_payload(summary))

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="heatsafe_daily_summaries.csv"'
    return response


@require_GET
def health_check(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        database_ok = cursor.fetchone() == (1,)
    return JsonResponse({"status": "ok", "database": database_ok})
