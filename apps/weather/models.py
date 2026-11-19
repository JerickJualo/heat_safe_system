from django.db import models


class Location(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    province = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timezone = models.CharField(max_length=64, default="Asia/Manila")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class WeatherRecord(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="weather_records")
    recorded_at = models.DateTimeField()
    temperature_2m = models.FloatField(null=True, blank=True)
    relative_humidity_2m = models.FloatField(null=True, blank=True)
    dew_point_2m = models.FloatField(null=True, blank=True)
    wind_speed_10m = models.FloatField(null=True, blank=True)
    precipitation = models.FloatField(null=True, blank=True)
    cloud_cover = models.FloatField(null=True, blank=True)
    shortwave_radiation = models.FloatField(null=True, blank=True)
    quality_flag = models.CharField(max_length=64, default="valid")
    is_valid_for_analysis = models.BooleanField(default=False)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["location", "recorded_at"], name="unique_weather_location_timestamp")
        ]
        indexes = [
            models.Index(fields=["location", "recorded_at"], name="weather_location_time_idx"),
            models.Index(fields=["recorded_at"], name="weather_recorded_at_idx"),
        ]
        ordering = ["location", "recorded_at"]


class HeatIndexRecord(models.Model):
    weather_record = models.OneToOneField(
        WeatherRecord, on_delete=models.CASCADE, related_name="heat_index_record"
    )
    heat_index_celsius = models.FloatField()
    risk_category = models.CharField(max_length=32)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["risk_category"], name="heat_risk_category_idx")]


class DailyWeatherSummary(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="daily_summaries")
    local_date = models.DateField()
    daily_valid_hour_count = models.PositiveSmallIntegerField(default=0)
    daily_expected_hour_count = models.PositiveSmallIntegerField(default=24)
    daily_complete = models.BooleanField(default=False)
    maximum_temperature = models.FloatField(null=True, blank=True)
    minimum_temperature = models.FloatField(null=True, blank=True)
    mean_temperature = models.FloatField(null=True, blank=True)
    maximum_relative_humidity = models.FloatField(null=True, blank=True)
    mean_relative_humidity = models.FloatField(null=True, blank=True)
    mean_wind_speed = models.FloatField(null=True, blank=True)
    maximum_wind_speed = models.FloatField(null=True, blank=True)
    total_precipitation = models.FloatField(null=True, blank=True)
    mean_cloud_cover = models.FloatField(null=True, blank=True)
    mean_solar_radiation = models.FloatField(null=True, blank=True)
    maximum_hourly_heat_index = models.FloatField(null=True, blank=True)
    average_heat_index = models.FloatField(null=True, blank=True)
    daytime_valid_hour_count = models.PositiveSmallIntegerField(default=0)
    daytime_expected_hour_count = models.PositiveSmallIntegerField(default=7)
    daytime_complete = models.BooleanField(default=False)
    maximum_daytime_heat_index = models.FloatField(null=True, blank=True)
    daily_risk_category = models.CharField(max_length=32, blank=True)
    data_quality_flag = models.CharField(max_length=80, default="incomplete_day_insufficient_hourly_coverage")
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["location", "local_date"], name="unique_daily_location_date")
        ]
        indexes = [
            models.Index(fields=["location", "local_date"], name="daily_location_date_idx"),
            models.Index(fields=["local_date"], name="daily_local_date_idx"),
            models.Index(fields=["daily_risk_category"], name="daily_risk_category_idx"),
        ]
        ordering = ["location", "local_date"]


class PredictionRecord(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="predictions")
    feature_date = models.DateField()
    target_date = models.DateField()
    model_name = models.CharField(max_length=120)
    predicted_heat_index_celsius = models.FloatField()
    model_metadata = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location", "target_date", "model_name"],
                name="unique_prediction_location_target_model",
            )
        ]
        indexes = [
            models.Index(fields=["location", "target_date"], name="prediction_location_date_idx"),
            models.Index(fields=["target_date"], name="prediction_target_date_idx"),
        ]
        ordering = ["-target_date", "location"]


class ModelEvaluation(models.Model):
    model_name = models.CharField(max_length=120)
    split = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    mae = models.FloatField()
    rmse = models.FloatField()
    r2 = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["model_name", "split"], name="unique_model_evaluation_split")
        ]
        ordering = ["split", "mae", "model_name"]
