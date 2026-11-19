"""Leakage-aware feature engineering for next-day heat-index forecasting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


TARGET_COLUMN = "target_next_day_maximum_daytime_heat_index"
MULTI_HORIZON_TARGET_COLUMN = "target_horizon_maximum_daytime_heat_index"
DATE_COLUMN = "feature_date"
TARGET_DATE_COLUMN = "target_date"
LOCATION_COLUMN = "location_name"

CURRENT_WEATHER_FEATURES = [
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
    "average_heat_index",
    "maximum_daytime_heat_index",
]
LAG_FEATURES = [
    "maximum_daytime_heat_index_lag_1",
    "maximum_daytime_heat_index_lag_2",
]
ROLLING_FEATURES = [
    "maximum_daytime_heat_index_rolling_3_previous_mean",
    "maximum_daytime_heat_index_rolling_7_previous_mean",
]
SEASONAL_FEATURES = [
    "month_sin",
    "month_cos",
    "day_of_year_sin",
    "day_of_year_cos",
]
NUMERIC_FEATURES = CURRENT_WEATHER_FEATURES + LAG_FEATURES + ROLLING_FEATURES + SEASONAL_FEATURES
CATEGORICAL_FEATURES = [LOCATION_COLUMN]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

REQUIRED_DAILY_COLUMNS = [
    "location_slug",
    "location_name",
    "local_date",
    "daily_complete",
    "daytime_complete",
    *CURRENT_WEATHER_FEATURES,
]


def _validate_daily_schema(daily: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_DAILY_COLUMNS).difference(daily.columns))
    if missing:
        raise ValueError(f"Daily dataset is missing required columns: {missing}")


def _add_seasonal_features(frame: pd.DataFrame) -> pd.DataFrame:
    day_of_year = frame[DATE_COLUMN].dt.dayofyear.astype(float)
    frame["month_sin"] = np.sin(2.0 * np.pi * frame[DATE_COLUMN].dt.month / 12.0)
    frame["month_cos"] = np.cos(2.0 * np.pi * frame[DATE_COLUMN].dt.month / 12.0)
    frame["day_of_year_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
    frame["day_of_year_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.25)
    return frame


def build_feature_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """Build one row per forecast date using only information known by that date.

    The row's features describe the current complete day and prior observations.
    Its target is the following day's maximum daytime heat index. Rolling features
    are explicitly computed from ``shift(1)`` so the current day's value is not
    included in a historical rolling statistic.
    """
    _validate_daily_schema(daily)
    frame = daily.copy()
    frame[DATE_COLUMN] = pd.to_datetime(frame["local_date"], errors="coerce")
    if frame[DATE_COLUMN].isna().any():
        raise ValueError("Daily dataset contains unparseable local_date values.")

    boolean_columns = ["daily_complete", "daytime_complete"]
    for column in boolean_columns:
        frame[column] = frame[column].astype(bool)
    for column in CURRENT_WEATHER_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    usable = frame[frame["daily_complete"] & frame["daytime_complete"]].copy()
    usable = usable.sort_values(["location_slug", DATE_COLUMN]).reset_index(drop=True)
    usable = usable.dropna(subset=CURRENT_WEATHER_FEATURES)

    grouped = usable.groupby("location_slug", sort=False, group_keys=False)
    usable["maximum_daytime_heat_index_lag_1"] = grouped[
        "maximum_daytime_heat_index"
    ].shift(1)
    usable["maximum_daytime_heat_index_lag_2"] = grouped[
        "maximum_daytime_heat_index"
    ].shift(2)
    previous = grouped["maximum_daytime_heat_index"].shift(1)
    usable["maximum_daytime_heat_index_rolling_3_previous_mean"] = (
        previous.groupby(usable["location_slug"]).rolling(3, min_periods=3).mean().reset_index(level=0, drop=True)
    )
    usable["maximum_daytime_heat_index_rolling_7_previous_mean"] = (
        previous.groupby(usable["location_slug"]).rolling(7, min_periods=7).mean().reset_index(level=0, drop=True)
    )
    usable[TARGET_COLUMN] = grouped["maximum_daytime_heat_index"].shift(-1)
    usable[TARGET_DATE_COLUMN] = grouped[DATE_COLUMN].shift(-1)
    usable = _add_seasonal_features(usable)

    usable[TARGET_DATE_COLUMN] = pd.to_datetime(usable[TARGET_DATE_COLUMN])
    usable["forecast_horizon_days"] = (
        usable[TARGET_DATE_COLUMN] - usable[DATE_COLUMN]
    ).dt.days
    observed_target = usable[TARGET_COLUMN].notna()
    if not usable.loc[observed_target, "forecast_horizon_days"].eq(1).all():
        raise ValueError("Feature rows must forecast exactly the next calendar day.")
    return usable.sort_values([DATE_COLUMN, "location_slug"]).reset_index(drop=True)


def build_ml_dataset(daily: pd.DataFrame) -> pd.DataFrame:
    """Build the supervised dataset, excluding warm-up and unavailable targets."""
    frame = build_feature_frame(daily)
    result = frame.dropna(subset=[*NUMERIC_FEATURES, TARGET_COLUMN, TARGET_DATE_COLUMN]).copy()
    if result[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("Feature engineering produced missing model inputs.")
    return result.sort_values([TARGET_DATE_COLUMN, "location_slug"]).reset_index(drop=True)


def build_multi_horizon_dataset(daily: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    """Build a direct forecast dataset for a bounded future horizon.

    Features describe the selected complete day and prior observations only. The
    target is the observed maximum daytime heat index exactly ``horizon_days``
    calendar days later. Requiring an exact target date prevents gaps from being
    silently treated as a shorter forecast horizon.
    """
    if not isinstance(horizon_days, int) or not 1 <= horizon_days <= 5:
        raise ValueError("horizon_days must be an integer from 1 through 5.")

    frame = build_feature_frame(daily)
    target_source = frame[
        [LOCATION_COLUMN, DATE_COLUMN, "maximum_daytime_heat_index"]
    ].rename(
        columns={
            DATE_COLUMN: "target_date",
            "maximum_daytime_heat_index": MULTI_HORIZON_TARGET_COLUMN,
        }
    )
    result = frame.copy()
    result[TARGET_DATE_COLUMN] = result[DATE_COLUMN] + pd.to_timedelta(int(horizon_days), unit="D")
    result = result.drop(columns=[TARGET_COLUMN], errors="ignore")
    result = result.merge(
        target_source,
        left_on=[LOCATION_COLUMN, TARGET_DATE_COLUMN],
        right_on=[LOCATION_COLUMN, "target_date"],
        how="inner",
        suffixes=("", "_observed"),
    )
    result = result.drop(columns=["target_date_observed"], errors="ignore")
    result["forecast_horizon_days"] = horizon_days
    result = result.dropna(subset=[*NUMERIC_FEATURES, MULTI_HORIZON_TARGET_COLUMN])
    if result[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("Multi-horizon feature engineering produced missing model inputs.")
    return result.sort_values([TARGET_DATE_COLUMN, LOCATION_COLUMN]).reset_index(drop=True)


def load_and_build_ml_dataset(path: Path) -> pd.DataFrame:
    return build_ml_dataset(pd.read_csv(path))


def split_by_target_date(
    dataset: pd.DataFrame,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Split by unique target dates, preserving chronological order."""
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between 0 and 1.")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test period.")
    dates = sorted(pd.to_datetime(dataset[TARGET_DATE_COLUMN]).dt.date.unique())
    if len(dates) < 3:
        raise ValueError("At least three target dates are required for a chronological split.")
    train_end = max(1, int(len(dates) * train_fraction))
    validation_end = max(train_end + 1, int(len(dates) * (train_fraction + validation_fraction)))
    validation_end = min(validation_end, len(dates) - 1)
    train_dates = set(dates[:train_end])
    validation_dates = set(dates[train_end:validation_end])
    test_dates = set(dates[validation_end:])
    train = dataset[pd.to_datetime(dataset[TARGET_DATE_COLUMN]).dt.date.isin(train_dates)].copy()
    validation = dataset[pd.to_datetime(dataset[TARGET_DATE_COLUMN]).dt.date.isin(validation_dates)].copy()
    test = dataset[pd.to_datetime(dataset[TARGET_DATE_COLUMN]).dt.date.isin(test_dates)].copy()
    if not (train[TARGET_DATE_COLUMN].max() < validation[TARGET_DATE_COLUMN].min() < test[TARGET_DATE_COLUMN].min()):
        raise AssertionError("Chronological split contains overlapping or unordered dates.")
    metadata = {
        "train": {"start": str(train[TARGET_DATE_COLUMN].min().date()), "end": str(train[TARGET_DATE_COLUMN].max().date()), "rows": int(len(train))},
        "validation": {"start": str(validation[TARGET_DATE_COLUMN].min().date()), "end": str(validation[TARGET_DATE_COLUMN].max().date()), "rows": int(len(validation))},
        "test": {"start": str(test[TARGET_DATE_COLUMN].min().date()), "end": str(test[TARGET_DATE_COLUMN].max().date()), "rows": int(len(test))},
        "unique_target_dates": len(dates),
    }
    return train, validation, test, metadata


def assert_no_target_leakage(feature_columns: list[str] | tuple[str, ...]) -> None:
    forbidden = {TARGET_COLUMN, TARGET_DATE_COLUMN, "future", "next_day"}
    if set(feature_columns) & forbidden:
        raise AssertionError(f"Target or future information found in model features: {set(feature_columns) & forbidden}")
    if any(column not in FEATURE_COLUMNS for column in feature_columns):
        raise AssertionError("Unexpected column included in the model feature list.")
