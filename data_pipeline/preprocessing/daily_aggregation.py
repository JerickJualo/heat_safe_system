"""Daily analytical aggregation for HeatSafe."""

from __future__ import annotations

import pandas as pd

from .heat_index import classify_heat_index


EXPECTED_HOURLY_COUNT = 24
EXPECTED_DAYTIME_COUNT = 7


def _aggregate_location_date(group: pd.DataFrame) -> pd.Series:
    daytime = group[group["is_daytime"] & group["is_valid_for_analysis"]]
    valid = group[group["is_valid_for_analysis"]]
    maximum_daytime_heat_index = daytime["heat_index_celsius"].max()
    return pd.Series(
        {
            "daily_valid_hour_count": int(len(valid)),
            "daily_expected_hour_count": EXPECTED_HOURLY_COUNT,
            "daily_complete": len(valid) == EXPECTED_HOURLY_COUNT,
            "maximum_temperature": valid["temperature_2m"].max(),
            "minimum_temperature": valid["temperature_2m"].min(),
            "mean_temperature": valid["temperature_2m"].mean(),
            "maximum_relative_humidity": valid["relative_humidity_2m"].max(),
            "mean_relative_humidity": valid["relative_humidity_2m"].mean(),
            "mean_wind_speed": valid["wind_speed_10m"].mean(),
            "maximum_wind_speed": valid["wind_speed_10m"].max(),
            "total_precipitation": valid["precipitation"].sum(min_count=1),
            "mean_cloud_cover": valid["cloud_cover"].mean(),
            "mean_solar_radiation": valid["shortwave_radiation"].mean(),
            "maximum_hourly_heat_index": valid["heat_index_celsius"].max(),
            "average_heat_index": valid["heat_index_celsius"].mean(),
            "daytime_valid_hour_count": int(len(daytime)),
            "daytime_expected_hour_count": EXPECTED_DAYTIME_COUNT,
            "daytime_complete": len(daytime) == EXPECTED_DAYTIME_COUNT,
            "maximum_daytime_heat_index": maximum_daytime_heat_index,
            "daily_risk_category": classify_heat_index(maximum_daytime_heat_index),
            "data_quality_flag": (
                "complete_day"
                if len(valid) == EXPECTED_HOURLY_COUNT
                else "incomplete_day_insufficient_hourly_coverage"
            ),
        }
    )


def aggregate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cleaned hourly data by location and local calendar date."""
    group_columns = ["location_slug", "location_name", "province", "local_date"]
    daily = (
        frame.groupby(group_columns, dropna=False, sort=True)
        .apply(_aggregate_location_date, include_groups=False)
        .reset_index()
    )
    return daily
