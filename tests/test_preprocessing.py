import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_pipeline.preprocessing.cleaning import clean_hourly_weather
from data_pipeline.preprocessing.daily_aggregation import aggregate_daily


class PreprocessingTests(unittest.TestCase):
    def _hourly_frame(self, rows: int = 24) -> pd.DataFrame:
        timestamps = pd.date_range("2026-01-01 00:00", periods=rows, freq="h", tz="Asia/Manila")
        return pd.DataFrame(
            {
                "location_slug": "test_city",
                "location_name": "Test City",
                "province": "Test Province",
                "recorded_at": timestamps.astype(str),
                "temperature_2m": 30.0,
                "relative_humidity_2m": 75.0,
                "dew_point_2m": 25.0,
                "wind_speed_10m": 2.0,
                "precipitation": 0.0,
                "cloud_cover": 50.0,
                "shortwave_radiation": 100.0,
            }
        )

    def test_cleaning_and_daily_aggregation_preserve_timezone_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_city_hourly.csv"
            self._hourly_frame().to_csv(path, index=False)
            hourly, report = clean_hourly_weather(path)
        self.assertEqual(report["valid_record_count"], 24)
        self.assertTrue(hourly["recorded_at"].dt.tz is not None)
        daily = aggregate_daily(hourly)
        self.assertEqual(len(daily), 1)
        self.assertTrue(bool(daily.iloc[0]["daily_complete"]))
        self.assertTrue(bool(daily.iloc[0]["daytime_complete"]))
        self.assertEqual(int(daily.iloc[0]["daytime_valid_hour_count"]), 7)

    def test_cleaning_flags_missing_required_values(self):
        frame = self._hourly_frame()
        frame.loc[0, "relative_humidity_2m"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_city_hourly.csv"
            frame.to_csv(path, index=False)
            hourly, report = clean_hourly_weather(path)
        self.assertEqual(report["invalid_record_count"], 1)
        self.assertEqual(hourly.loc[0, "quality_flag"], "missing_required_input")
        self.assertFalse(bool(hourly.loc[0, "is_valid_for_analysis"]))

