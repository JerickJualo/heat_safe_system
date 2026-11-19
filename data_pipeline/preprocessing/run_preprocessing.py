"""Run HeatSafe cleaning, heat-index calculation, and daily aggregation."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .cleaning import clean_hourly_weather
from .daily_aggregation import aggregate_daily


LOGGER = logging.getLogger("heatsafe.preprocessing")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def run() -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    reports = {}
    hourly_frames = []
    for raw_path in sorted(RAW_DIR.glob("*_city_hourly.csv")):
        LOGGER.info("Processing %s", raw_path.name)
        hourly, report = clean_hourly_weather(raw_path)
        slug = raw_path.name.removesuffix("_hourly.csv")
        hourly_path = PROCESSED_DIR / f"{slug}_hourly_heat_index.csv"
        valid_hourly_path = PROCESSED_DIR / f"{slug}_hourly_heat_index_valid.csv"
        hourly.to_csv(hourly_path, index=False, encoding="utf-8")
        hourly[hourly["is_valid_for_analysis"]].to_csv(
            valid_hourly_path, index=False, encoding="utf-8"
        )
        report["processed_hourly_file"] = str(hourly_path)
        report["processed_valid_hourly_file"] = str(valid_hourly_path)
        reports[slug] = report
        hourly_frames.append(hourly)

    if not hourly_frames:
        raise FileNotFoundError(f"No raw hourly CSV files found in {RAW_DIR}")

    all_hourly = pd.concat(hourly_frames, ignore_index=True)
    daily = aggregate_daily(all_hourly)
    daily_path = PROCESSED_DIR / "daily_heat_index.csv"
    daily.to_csv(daily_path, index=False, encoding="utf-8")

    summary = {
        "source_directory": str(RAW_DIR),
        "processed_directory": str(PROCESSED_DIR),
        "locations": reports,
        "combined_hourly_file": str(PROCESSED_DIR / "all_locations_hourly_heat_index.csv"),
        "daily_file": str(daily_path),
        "daily_record_count": int(len(daily)),
        "daily_complete_count": int(daily["daily_complete"].sum()),
        "daytime_complete_count": int(daily["daytime_complete"].sum()),
    }
    all_hourly.to_csv(
        PROCESSED_DIR / "all_locations_hourly_heat_index.csv",
        index=False,
        encoding="utf-8",
    )
    write_json(PROCESSED_DIR / "preprocessing_summary.json", summary)
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
