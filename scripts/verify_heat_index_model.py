"""Verify the saved Phase 4 model with actual recent valid daily inputs."""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.ml.inference import (  # noqa: E402
    predict_next_day_maximum_daytime_heat_index,
    prepare_next_day_features,
)


def main() -> int:
    daily_path = PROJECT_ROOT / "data" / "processed" / "daily_heat_index.csv"
    model_path = PROJECT_ROOT / "models" / "phase4" / "heat_index_next_day_model.joblib"
    output_path = PROJECT_ROOT / "data" / "processed" / "ml" / "inference_verification.json"
    daily = pd.read_csv(daily_path)
    results = []
    for location in sorted(daily["location_name"].unique()):
        history = daily[daily["location_name"] == location].copy()
        features = prepare_next_day_features(history)
        prediction = predict_next_day_maximum_daytime_heat_index(model_path, history)
        results.append(
            {
                "location_name": location,
                "latest_feature_date": features["feature_date"].iloc[0].date().isoformat(),
                "prediction_target_date": (features["feature_date"].iloc[0] + pd.Timedelta(value=1, unit="D")).date().isoformat(),
                "prediction_celsius": prediction,
                "numeric_prediction": isinstance(prediction, float),
            }
        )
    output_path.write_text(json.dumps({"model_file": str(model_path), "results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
