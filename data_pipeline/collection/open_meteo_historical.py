"""Collect and validate HeatSafe hourly historical weather data.

The collector uses only the Open-Meteo Historical Weather API with the ERA5
reanalysis model. It keeps the API response for every batch, writes one raw
CSV per location, and produces machine-readable collection and validation
reports.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


LOGGER = logging.getLogger("heatsafe.open_meteo")
API_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE_URL = "https://open-meteo.com/en/docs/historical-weather-api"
MODEL = "era5"
LOCAL_TZ = ZoneInfo("Asia/Manila")
START_DATE = date(2017, 1, 1)
COMPLETE_YEAR_END = date(2025, 12, 31)
EARLIEST_2026_DATE = date(2026, 1, 1)

HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
)

EXPECTED_UNITS = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "dew_point_2m": "°C",
    "wind_speed_10m": "km/h",
    "precipitation": "mm",
    "cloud_cover": "%",
    "shortwave_radiation": "W/m²",
}

VALIDATION_RANGES = {
    "temperature_2m": (-60.0, 60.0),
    "relative_humidity_2m": (0.0, 100.0),
    "dew_point_2m": (-80.0, 60.0),
    "wind_speed_10m": (0.0, None),
    "precipitation": (0.0, None),
    "cloud_cover": (0.0, 100.0),
    "shortwave_radiation": (0.0, None),
}


@dataclass(frozen=True)
class Location:
    slug: str
    name: str
    province: str
    latitude: float
    longitude: float


LOCATIONS = (
    Location("surigao_city", "Surigao City", "Surigao del Norte", 9.7842, 125.4888),
    Location("butuan_city", "Butuan City", "Agusan del Norte", 8.9475, 125.5406),
    Location("davao_city", "Davao City", "Davao del Sur", 7.1907, 125.4553),
)


def build_session() -> requests.Session:
    """Create a session with bounded retries for transient API failures."""
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "HeatSafe/0.1 historical-data-collector",
            "Accept": "application/json",
        }
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def current_local_date() -> date:
    """Return today's date in the application's timezone."""
    return datetime.now(LOCAL_TZ).date()


def build_batches(start: date, end: date) -> list[tuple[date, date]]:
    """Split a range into calendar-year API requests."""
    batches: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        batch_end = min(date(cursor.year, 12, 31), end)
        batches.append((cursor, batch_end))
        cursor = batch_end + timedelta(days=1)
    return batches


def parse_api_timestamps(values: list[str]) -> pd.Series:
    """Parse API timestamps and normalize them to Asia/Manila."""
    parsed = pd.to_datetime(pd.Series(values), errors="coerce")
    if parsed.isna().any():
        raise ValueError("The API returned an invalid hourly timestamp.")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(LOCAL_TZ)
    else:
        parsed = parsed.dt.tz_convert(LOCAL_TZ)
    return parsed


def request_batch(
    session: requests.Session,
    location: Location,
    batch_start: date,
    batch_end: date,
) -> dict[str, Any]:
    """Request one location and date batch from the explicit ERA5 model."""
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": batch_start.isoformat(),
        "end_date": batch_end.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "models": MODEL,
        "timezone": "Asia/Manila",
        "timeformat": "iso8601",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "cell_selection": "land",
    }
    LOGGER.info("Requesting %s: %s to %s", location.name, batch_start, batch_end)
    response = session.get(API_URL, params=params, timeout=(15, 180))
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Open-Meteo returned an error."))
    if "hourly" not in payload or "time" not in payload["hourly"]:
        raise RuntimeError("Open-Meteo response did not contain hourly time data.")
    return payload


def payload_to_frame(payload: dict[str, Any], location: Location) -> pd.DataFrame:
    """Convert one validated API response into a normalized hourly frame."""
    hourly = payload["hourly"]
    times = hourly["time"]
    lengths = {key: len(hourly.get(key, [])) for key in ("time", *HOURLY_VARIABLES)}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"Hourly arrays have inconsistent lengths: {lengths}")
    missing = [key for key in HOURLY_VARIABLES if key not in hourly]
    if missing:
        raise ValueError(f"Required hourly variables are missing: {missing}")
    returned_units = payload.get("hourly_units", {})
    unit_errors = {
        key: {"expected": EXPECTED_UNITS[key], "received": returned_units.get(key)}
        for key in HOURLY_VARIABLES
        if returned_units.get(key) != EXPECTED_UNITS[key]
    }
    if unit_errors:
        raise ValueError(f"Open-Meteo returned unexpected units: {unit_errors}")

    frame = pd.DataFrame({key: hourly[key] for key in HOURLY_VARIABLES})
    frame.insert(0, "recorded_at", parse_api_timestamps(times))
    for column in HOURLY_VARIABLES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame.insert(0, "location_slug", location.slug)
    frame.insert(1, "location_name", location.name)
    frame.insert(2, "province", location.province)
    frame.insert(3, "requested_latitude", location.latitude)
    frame.insert(4, "requested_longitude", location.longitude)
    return frame


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def expected_hourly_range(start: date, end: date) -> pd.DatetimeIndex:
    """Return every expected local hourly timestamp in an inclusive range."""
    start_dt = datetime.combine(start, time.min, tzinfo=LOCAL_TZ)
    end_dt = datetime.combine(end, time(23), tzinfo=LOCAL_TZ)
    return pd.date_range(start=start_dt, end=end_dt, freq="h")


def json_number(value: Any) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def validate_frame(
    frame: pd.DataFrame,
    location: Location,
    requested_end: date,
    batch_errors: list[str],
) -> dict[str, Any]:
    """Validate timestamps, variables, values, gaps, and 2026 partial coverage."""
    frame = frame.copy()
    frame["recorded_at"] = parse_api_timestamps(frame["recorded_at"].astype(str).tolist())
    frame = frame.sort_values("recorded_at")
    timestamp_series = frame["recorded_at"]
    available_mask = frame[list(HOURLY_VARIABLES)].notna().any(axis=1)
    available_timestamps = timestamp_series[available_mask]
    first_available = available_timestamps.min() if not available_timestamps.empty else None
    last_available = available_timestamps.max() if not available_timestamps.empty else None

    duplicate_count = int(timestamp_series.duplicated().sum())
    available_record_count = int(available_mask.sum())
    trailing_unavailable_mask = (~available_mask) & (timestamp_series > last_available if last_available is not None else True)
    trailing_unavailable_count = int(trailing_unavailable_mask.sum())
    complete_period_missing_values = int(
        frame.loc[frame["recorded_at"].dt.date <= COMPLETE_YEAR_END, list(HOURLY_VARIABLES)]
        .isna()
        .sum()
        .sum()
    )
    missing_values = {
        column: int(frame[column].isna().sum()) for column in HOURLY_VARIABLES
    }
    invalid_values: dict[str, int] = {}
    for column, (minimum, maximum) in VALIDATION_RANGES.items():
        values = frame[column].dropna()
        invalid = pd.Series(False, index=values.index)
        if minimum is not None:
            invalid |= values < minimum
        if maximum is not None:
            invalid |= values > maximum
        invalid_values[column] = int(invalid.sum())

    complete_expected = expected_hourly_range(START_DATE, COMPLETE_YEAR_END)
    complete_actual = pd.DatetimeIndex(
        timestamp_series[(timestamp_series.dt.date >= START_DATE) & (timestamp_series.dt.date <= COMPLETE_YEAR_END)]
    ).drop_duplicates()
    complete_missing = int(len(complete_expected.difference(complete_actual)))

    partial_actual = frame.loc[
        frame["recorded_at"].dt.date >= EARLIEST_2026_DATE, "recorded_at"
    ].drop_duplicates()
    if partial_actual.empty:
        partial_expected = pd.DatetimeIndex([])
        partial_missing = 0
    else:
        partial_expected = expected_hourly_range(EARLIEST_2026_DATE, partial_actual.max().date())
        partial_missing = int(len(partial_expected.difference(pd.DatetimeIndex(partial_actual))))

    by_year = frame.assign(year=frame["recorded_at"].dt.year).groupby("year").size()
    year_summary: dict[str, Any] = {}
    for year in range(2017, 2026):
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        expected_count = len(expected_hourly_range(year_start, year_end))
        actual_count = int(by_year.get(year, 0))
        year_summary[str(year)] = {
            "status": "complete" if actual_count == expected_count else "incomplete",
            "expected_records": expected_count,
            "actual_records": actual_count,
            "missing_records": max(expected_count - actual_count, 0),
        }
    actual_2026 = int(by_year.get(2026, 0))
    year_summary["2026"] = {
        "status": "partial",
        "expected_records": None,
        "actual_records": actual_2026,
        "missing_records": None,
    }

    requested_latest = datetime.combine(requested_end, time(23), tzinfo=LOCAL_TZ)
    delay_days = None
    if last_available is not None:
        delay_days = (requested_latest.date() - last_available.date()).days
    if batch_errors:
        availability_cause = "collection_error"
    elif delay_days is not None and delay_days >= 4:
        availability_cause = "likely_era5_update_delay"
    elif delay_days is not None and delay_days > 0:
        availability_cause = "api_returned_no_later_observations_review_needed"
    else:
        availability_cause = "no_observed_end_date_delay"

    return {
        "location": asdict(location),
        "model": MODEL,
        "api_url": API_URL,
        "source_documentation": SOURCE_URL,
        "timezone": "Asia/Manila",
        "units": EXPECTED_UNITS,
        "requested_period": {
            "complete_years": "2017-01-01 through 2025-12-31",
            "partial_year": f"2026-01-01 through {requested_end.isoformat()} requested; actual API coverage determines the end",
        },
        "first_available_timestamp": first_available.isoformat() if first_available is not None else None,
        "last_available_timestamp": last_available.isoformat() if last_available is not None else None,
        "record_count": int(len(frame)),
        "available_record_count": available_record_count,
        "trailing_unavailable_row_count": trailing_unavailable_count,
        "unique_timestamp_count": int(timestamp_series.nunique()),
        "duplicate_timestamp_count": duplicate_count,
        "missing_values_by_column": missing_values,
        "invalid_values_by_column": invalid_values,
        "missing_complete_period_timestamps": complete_missing,
        "missing_partial_period_timestamps": partial_missing,
        "year_summary": year_summary,
        "2026_end_date_delay_days": delay_days,
        "2026_missing_data_cause": availability_cause,
        "batch_errors": batch_errors,
        "validation_passed": not batch_errors
        and duplicate_count == 0
        and complete_missing == 0
        and complete_period_missing_values == 0
        and trailing_unavailable_count == int(frame[list(HOURLY_VARIABLES)].isna().all(axis=1).sum())
        and all(value == 0 for value in invalid_values.values()),
    }


def collect_location(
    session: requests.Session,
    location: Location,
    output_dir: Path,
    requested_end: date,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Collect all batches for one location and return its report and frame."""
    location_response_dir = output_dir / "api_responses" / location.slug
    frames: list[pd.DataFrame] = []
    batch_errors: list[str] = []
    response_metadata: list[dict[str, Any]] = []

    for batch_start, batch_end in build_batches(START_DATE, requested_end):
        response_path = location_response_dir / f"{batch_start.isoformat()}_to_{batch_end.isoformat()}.json"
        try:
            use_cache = batch_end <= COMPLETE_YEAR_END and response_path.exists()
            if use_cache:
                LOGGER.info("Using cached response for %s: %s to %s", location.name, batch_start, batch_end)
                payload = json.loads(response_path.read_text(encoding="utf-8"))
            else:
                payload = request_batch(session, location, batch_start, batch_end)
                write_json(response_path, payload)
            frames.append(payload_to_frame(payload, location))
            response_metadata.append(
                {
                    "batch_start": batch_start.isoformat(),
                    "batch_end": batch_end.isoformat(),
                    "response_file": str(response_path),
                    "api_timezone": payload.get("timezone"),
                    "api_utc_offset_seconds": payload.get("utc_offset_seconds"),
                    "api_grid_latitude": payload.get("latitude"),
                    "api_grid_longitude": payload.get("longitude"),
                    "api_elevation": payload.get("elevation"),
                    "hourly_units": payload.get("hourly_units"),
                }
            )
        except Exception as exc:  # keep other locations progressing; report failure
            error = f"{batch_start.isoformat()} to {batch_end.isoformat()}: {exc}"
            LOGGER.exception("Batch failed for %s", location.name)
            batch_errors.append(error)

    if frames:
        frame = pd.concat(frames, ignore_index=True)
    else:
        frame = pd.DataFrame(columns=["location_slug", "location_name", "province", "requested_latitude", "requested_longitude", "recorded_at", *HOURLY_VARIABLES])

    raw_duplicate_count = int(frame["recorded_at"].duplicated().sum())
    frame = frame.sort_values("recorded_at").drop_duplicates(subset=["recorded_at"], keep="first")
    csv_path = output_dir / f"{location.slug}_hourly.csv"
    frame.to_csv(csv_path, index=False, encoding="utf-8")
    report = validate_frame(frame, location, requested_end, batch_errors)
    report["duplicate_timestamp_count_before_deduplication"] = raw_duplicate_count
    report["duplicates_removed"] = raw_duplicate_count
    report["raw_csv"] = str(csv_path)
    report["api_batches"] = response_metadata
    report["collection_generated_at"] = datetime.now(LOCAL_TZ).isoformat()
    write_json(output_dir / f"{location.slug}_metadata.json", report)
    return report, frame


def run_collection(output_dir: Path) -> dict[str, Any]:
    """Collect all configured locations and write summary artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    requested_end = current_local_date()
    LOGGER.info("Collection requested through %s in %s", requested_end, LOCAL_TZ)
    reports: list[dict[str, Any]] = []
    with build_session() as session:
        for location in LOCATIONS:
            report, _ = collect_location(session, location, output_dir, requested_end)
            reports.append(report)

    summary = {
        "collection_generated_at": datetime.now(LOCAL_TZ).isoformat(),
        "requested_end_date": requested_end.isoformat(),
        "model": MODEL,
        "api_url": API_URL,
        "source_documentation": SOURCE_URL,
        "timezone": "Asia/Manila",
        "complete_years": "2017-01-01 through 2025-12-31",
        "partial_year": "2026 is partial and ends at the latest available API timestamp",
        "locations": reports,
        "all_locations_validation_passed": all(report["validation_passed"] for report in reports),
    }
    write_json(output_dir / "collection_summary.json", summary)
    write_json(output_dir / "validation_report.json", {"locations": reports})

    summary_rows = []
    for report in reports:
        summary_rows.append(
            {
                "location": report["location"]["name"],
                "model": report["model"],
                "first_available_timestamp": report["first_available_timestamp"],
                "last_available_timestamp": report["last_available_timestamp"],
                "record_count": report["record_count"],
                "available_record_count": report["available_record_count"],
                "trailing_unavailable_row_count": report["trailing_unavailable_row_count"],
                "unique_timestamp_count": report["unique_timestamp_count"],
                "duplicate_timestamp_count": report["duplicate_timestamp_count"],
                "duplicate_timestamp_count_before_deduplication": report.get("duplicate_timestamp_count_before_deduplication", 0),
                "duplicates_removed": report.get("duplicates_removed", 0),
                "missing_complete_period_timestamps": report["missing_complete_period_timestamps"],
                "missing_partial_period_timestamps": report["missing_partial_period_timestamps"],
                "2026_end_date_delay_days": report["2026_end_date_delay_days"],
                "2026_missing_data_cause": report["2026_missing_data_cause"],
                "validation_passed": report["validation_passed"],
            }
        )
    pd.DataFrame(summary_rows).to_csv(output_dir / "collection_summary.csv", index=False, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "raw",
        help="Directory for raw CSV, JSON responses, metadata, and reports.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = run_collection(args.output_dir)
    LOGGER.info("Collection finished. All locations passed: %s", summary["all_locations_validation_passed"])
    return 0 if summary["all_locations_validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
