from datetime import date

from django.test import Client, TestCase

from .models import DailyWeatherSummary, Location, ModelEvaluation, PredictionRecord, WeatherRecord


class WeatherApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.create(
            slug="test_city",
            name="Test City",
            province="Test Province",
            latitude=8.0,
            longitude=125.0,
        )
        DailyWeatherSummary.objects.create(
            location=cls.location,
            local_date=date(2026, 1, 2),
            daily_valid_hour_count=24,
            daily_complete=True,
            maximum_daytime_heat_index=38.5,
            maximum_hourly_heat_index=39.0,
            average_heat_index=32.0,
            daily_risk_category="Extreme Caution",
            daytime_valid_hour_count=7,
            daytime_complete=True,
            maximum_temperature=32.0,
            mean_relative_humidity=75.0,
            total_precipitation=1.0,
            data_quality_flag="complete_day",
        )
        PredictionRecord.objects.create(
            location=cls.location,
            feature_date=date(2026, 1, 2),
            target_date=date(2026, 1, 3),
            model_name="linear_regression",
            predicted_heat_index_celsius=37.5,
        )
        ModelEvaluation.objects.create(
            model_name="linear_regression",
            split="validation",
            row_count=10,
            mae=1.0,
            rmse=1.2,
            r2=0.8,
        )
        WeatherRecord.objects.create(
            location=cls.location,
            recorded_at="2026-01-02T10:00:00+08:00",
            temperature_2m=31.0,
            relative_humidity_2m=75.0,
            quality_flag="valid",
            is_valid_for_analysis=True,
        )

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dashboard_endpoint_returns_location_data(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locations"][0]["slug"], "test_city")

    def test_analytics_rejects_unknown_location(self):
        response = self.client.get("/api/analytics/?location=unknown")
        self.assertEqual(response.status_code, 404)

    def test_analytics_and_comparison_endpoints(self):
        response = self.client.get("/api/analytics/?location=test_city&start_date=2026-01-01&end_date=2026-01-03")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("/api/locations/compare/?date=2026-01-02")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["locations"][0]["location"], "test_city")

    def test_prediction_and_report_endpoints(self):
        response = self.client.get("/api/predictions/?location=test_city")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = self.client.get("/api/report/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"]["predictions"], 1)

    def test_model_performance_and_csv_export(self):
        response = self.client.get("/api/model-performance/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["selected_model"], "linear_regression")
        self.assertEqual(response.json()["metrics"][0]["model_name"], "linear_regression")
        response = self.client.get("/api/export/daily.csv?location=test_city&start_date=2026-01-01&end_date=2026-01-03")
        self.assertEqual(response.status_code, 200)
        csv_body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("location,location_name,date", csv_body)
        self.assertIn("test_city,Test City,2026-01-02", csv_body)

    def test_input_validation_and_csrf_protection(self):
        response = self.client.get("/api/analytics/?start_date=2026-01-03&end_date=2026-01-01")
        self.assertEqual(response.status_code, 400)
        response = self.client.get("/api/export/daily.csv?start_date=not-a-date")
        self.assertEqual(response.status_code, 400)
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post("/api/predictions/generate/")
        self.assertEqual(response.status_code, 403)

    def test_multi_day_prediction_validation(self):
        response = self.client.get(
            "/api/predictions/forecast/?location=test_city&feature_date=2026-01-02&horizon=6"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            "/api/predictions/forecast/?location=test_city&feature_date=not-a-date"
        )
        self.assertEqual(response.status_code, 400)

