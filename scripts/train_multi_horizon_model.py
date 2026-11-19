"""Train the bounded one-to-five-day HeatSafe forecast models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.ml.multi_horizon import train_multi_horizon_models


PROJECT_ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    metadata = train_multi_horizon_models(
        PROJECT_ROOT / "data" / "processed" / "daily_heat_index.csv",
        PROJECT_ROOT / "models" / "phase4" / "heat_index_multi_horizon_model.joblib",
        PROJECT_ROOT / "data" / "processed" / "ml" / "multi_horizon_model_metadata.json",
    )
    print(metadata)
