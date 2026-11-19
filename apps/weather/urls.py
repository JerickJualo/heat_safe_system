from django.urls import path

from . import views


app_name = "weather"

urlpatterns = [
    path("health/", views.health_check, name="health"),
    path("dashboard/", views.dashboard_data, name="dashboard"),
    path("analytics/", views.analytics_data, name="analytics"),
    path("predictions/", views.prediction_data, name="predictions"),
    path("predictions/forecast/", views.multi_day_prediction_data, name="prediction_forecast"),
    path("predictions/generate/", views.generate_predictions, name="generate_predictions"),
    path("locations/compare/", views.location_comparison, name="location_comparison"),
    path("report/", views.report_data, name="report"),
    path("model-performance/", views.model_performance_data, name="model_performance"),
    path("export/daily.csv", views.export_daily_csv, name="export_daily_csv"),
]
