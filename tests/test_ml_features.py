import unittest

import pandas as pd

from data_pipeline.ml.features import (
    FEATURE_COLUMNS,
    MULTI_HORIZON_TARGET_COLUMN,
    TARGET_COLUMN,
    assert_no_target_leakage,
    build_feature_frame,
    build_ml_dataset,
    build_multi_horizon_dataset,
    split_by_target_date,
)


def make_daily_frame(days: int = 20, locations: int = 2) -> pd.DataFrame:
    rows = []
    names = [("loc_a", "Location A"), ("loc_b", "Location B")][:locations]
    for slug, name in names:
        for day in range(days):
            value = 30.0 + day + (0.5 if slug == "loc_b" else 0.0)
            rows.append(
                {
                    "location_slug": slug,
                    "location_name": name,
                    "local_date": (pd.Timestamp("2020-01-01") + pd.Timedelta(value=int(day), unit="D")).date().isoformat(),
                    "daily_complete": True,
                    "daytime_complete": True,
                    "maximum_temperature": 30.0,
                    "minimum_temperature": 24.0,
                    "mean_temperature": 27.0,
                    "maximum_relative_humidity": 90.0,
                    "mean_relative_humidity": 80.0,
                    "mean_wind_speed": 3.0,
                    "maximum_wind_speed": 6.0,
                    "total_precipitation": 1.0,
                    "mean_cloud_cover": 70.0,
                    "mean_solar_radiation": 200.0,
                    "average_heat_index": value - 1.0,
                    "maximum_daytime_heat_index": value,
                }
            )
    return pd.DataFrame(rows)


class MachineLearningFeatureTests(unittest.TestCase):
    def test_target_is_next_day_and_rolling_features_are_previous_only(self):
        daily = make_daily_frame(days=10, locations=1)
        engineered = build_feature_frame(daily)
        row = engineered[engineered["feature_date"] == pd.Timestamp("2020-01-08")].iloc[0]
        self.assertEqual(row["target_date"], pd.Timestamp("2020-01-09"))
        self.assertAlmostEqual(row["target_next_day_maximum_daytime_heat_index"], 38.0)
        self.assertAlmostEqual(row["maximum_daytime_heat_index_lag_1"], 36.0)
        self.assertAlmostEqual(row["maximum_daytime_heat_index_lag_2"], 35.0)
        self.assertAlmostEqual(row["maximum_daytime_heat_index_rolling_3_previous_mean"], 35.0)
        self.assertAlmostEqual(row["maximum_daytime_heat_index_rolling_7_previous_mean"], 33.0)

    def test_supervised_rows_exclude_missing_target_and_features_have_no_target(self):
        dataset = build_ml_dataset(make_daily_frame())
        self.assertTrue(dataset[TARGET_COLUMN].notna().all())
        self.assertTrue(dataset[FEATURE_COLUMNS].notna().all().all())
        assert_no_target_leakage(FEATURE_COLUMNS)

    def test_split_is_chronological(self):
        dataset = build_ml_dataset(make_daily_frame(days=40, locations=2))
        train, validation, test, metadata = split_by_target_date(dataset)
        self.assertLess(train["target_date"].max(), validation["target_date"].min())
        self.assertLess(validation["target_date"].max(), test["target_date"].min())
        self.assertEqual(metadata["train"]["rows"] + metadata["validation"]["rows"] + metadata["test"]["rows"], len(dataset))

    def test_multi_horizon_target_uses_exact_future_date(self):
        dataset = build_multi_horizon_dataset(make_daily_frame(days=20, locations=1), 5)
        row = dataset[dataset["feature_date"] == pd.Timestamp("2020-01-08")].iloc[0]
        self.assertEqual(row["target_date"], pd.Timestamp("2020-01-13"))
        self.assertAlmostEqual(row[MULTI_HORIZON_TARGET_COLUMN], 42.0)
        self.assertEqual(row["forecast_horizon_days"], 5)

    def test_multi_horizon_rejects_horizons_outside_one_to_five(self):
        with self.assertRaises(ValueError):
            build_multi_horizon_dataset(make_daily_frame(), 6)


if __name__ == "__main__":
    unittest.main()
