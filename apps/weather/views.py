"""JSON endpoints for dashboard, analytics, comparisons, reports, and predictions."""

from __future__ import annotations

from datetime import date

from django.db import connection
from django.http import JsonResponse
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
    if not summaries.exists():
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


@require_GET
def health_check(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        database_ok = cursor.fetchone() == (1,)
    return JsonResponse({"status": "ok", "database": database_ok})
