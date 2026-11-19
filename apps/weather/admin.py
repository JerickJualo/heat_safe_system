from django.contrib import admin

from .models import DailyWeatherSummary, HeatIndexRecord, Location, ModelEvaluation, PredictionRecord, WeatherRecord


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "latitude", "longitude", "is_active")
    search_fields = ("name", "province", "slug")


@admin.register(WeatherRecord)
class WeatherRecordAdmin(admin.ModelAdmin):
    list_display = ("location", "recorded_at", "temperature_2m", "relative_humidity_2m", "quality_flag")
    list_filter = ("location", "quality_flag", "is_valid_for_analysis")
    date_hierarchy = "recorded_at"


@admin.register(HeatIndexRecord)
class HeatIndexRecordAdmin(admin.ModelAdmin):
    list_display = ("weather_record", "heat_index_celsius", "risk_category")
    list_filter = ("risk_category",)


@admin.register(DailyWeatherSummary)
class DailyWeatherSummaryAdmin(admin.ModelAdmin):
    list_display = ("location", "local_date", "maximum_daytime_heat_index", "daily_risk_category", "daytime_complete")
    list_filter = ("location", "daily_risk_category", "daytime_complete")
    date_hierarchy = "local_date"


@admin.register(PredictionRecord)
class PredictionRecordAdmin(admin.ModelAdmin):
    list_display = ("location", "target_date", "predicted_heat_index_celsius", "model_name", "generated_at")
    list_filter = ("location", "model_name")


@admin.register(ModelEvaluation)
class ModelEvaluationAdmin(admin.ModelAdmin):
    list_display = ("model_name", "split", "mae", "rmse", "r2", "row_count")
    list_filter = ("model_name", "split")
