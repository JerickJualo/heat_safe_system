"""Cleaning and quality flagging for raw HeatSafe weather CSV files."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .heat_index import calculate_heat_index_series, classify_heat_index_series


LOCAL_TZ = ZoneInfo("Asia/Manila")
REQUIRED_WEATHER_COLUMNS = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
)

VALIDATION_RANGES = {
    "temperature_2m": (-60.0, 60.0),
    "relative_humidity_2m": (0.0, 100.0),
    "dew_point_2m": (-80.0, 60.0),
    "wind_speed_10m": (0.0, None),
    "precipitation": (0.0, None),
    "cloud_cover": (0.0, 100.0),
    "shortwave_radiation": (0.0, None),
}


def parse_local_timestamps(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any():
        raise ValueError("One or more timestamps could not be parsed.")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(LOCAL_TZ)
    else:
        parsed = parsed.dt.tz_convert(LOCAL_TZ)
    return parsed


def _range_invalid(frame: pd.DataFrame, column: str) -> pd.Series:
    minimum, maximum = VALIDATION_RANGES[column]
    invalid = pd.Series(False, index=frame.index)
    if minimum is not None:
        invalid |= frame[column] < minimum
    if maximum is not None:
        invalid |= frame[column] > maximum
    return invalid


def clean_hourly_weather(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    """Load, clean, flag, and calculate hourly heat index values."""
    frame = pd.read_csv(raw_path)
    required_columns = {"recorded_at", *REQUIRED_WEATHER_COLUMNS}
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns in {raw_path}: {missing_columns}")

    frame["recorded_at"] = parse_local_timestamps(frame["recorded_at"])
    for column in REQUIRED_WEATHER_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    duplicate_mask = frame.duplicated(subset=["location_slug", "recorded_at"], keep=False)
    invalid_masks = {column: _range_invalid(frame, column) for column in VALIDATION_RANGES}
    invalid_range_mask = pd.DataFrame(invalid_masks).any(axis=1)
    missing_input_mask = frame[list(REQUIRED_WEATHER_COLUMNS)].isna().any(axis=1)

    frame["quality_flag"] = np.select(
        [duplicate_mask, invalid_range_mask, missing_input_mask],
        ["duplicate_timestamp", "invalid_range", "missing_required_input"],
        default="valid",
    )
    frame["is_valid_for_analysis"] = frame["quality_flag"].eq("valid")
    frame["local_date"] = frame["recorded_at"].dt.date.astype(str)
    frame["local_hour"] = frame["recorded_at"].dt.hour
    frame["is_daytime"] = frame["local_hour"].between(10, 16)
    frame["heat_index_celsius"] = calculate_heat_index_series(
        frame["temperature_2m"], frame["relative_humidity_2m"]
    )
    frame.loc[~frame["is_valid_for_analysis"], "heat_index_celsius"] = np.nan
    frame["risk_category"] = classify_heat_index_series(frame["heat_index_celsius"])
    frame.loc[~frame["is_valid_for_analysis"], "risk_category"] = pd.NA

    report = {
        "source_file": str(raw_path),
        "record_count": int(len(frame)),
        "valid_record_count": int(frame["is_valid_for_analysis"].sum()),
        "invalid_record_count": int((~frame["is_valid_for_analysis"]).sum()),
        "quality_flag_counts": frame["quality_flag"].value_counts(dropna=False).to_dict(),
        "duplicate_timestamp_count": int(frame["recorded_at"].duplicated().sum()),
        "missing_values_by_column": {
            column: int(frame[column].isna().sum()) for column in REQUIRED_WEATHER_COLUMNS
        },
        "invalid_range_counts": {
            column: int(mask.sum()) for column, mask in invalid_masks.items()
        },
        "timezone": "Asia/Manila",
    }
    return frame, report
