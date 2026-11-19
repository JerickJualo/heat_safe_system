"""Train direct, leakage-aware heat-index models for horizons one through five."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from .evaluation import regression_metrics
from .features import (
    FEATURE_COLUMNS,
    MULTI_HORIZON_TARGET_COLUMN,
    build_multi_horizon_dataset,
    split_by_target_date,
)
from .evaluation import build_candidate_models


def train_multi_horizon_models(
    daily_path: Path,
    model_path: Path,
    metadata_path: Path,
    horizons: tuple[int, ...] = (1, 2, 3, 4, 5),
) -> dict:
    """Train one direct Linear Regression model for each requested horizon."""
    daily = pd.read_csv(daily_path)
    models: dict[str, dict] = {}
    metrics: list[dict] = []

    for horizon in horizons:
        if not 1 <= horizon <= 5:
            raise ValueError("All horizons must be between 1 and 5 days.")
        dataset = build_multi_horizon_dataset(daily, horizon)
        train, validation, test, split_metadata = split_by_target_date(dataset)
        model = build_candidate_models()["linear_regression"]
        model.fit(train[FEATURE_COLUMNS], train[MULTI_HORIZON_TARGET_COLUMN])
        validation_predictions = model.predict(validation[FEATURE_COLUMNS])
        metrics.append(
            {
                "horizon_days": horizon,
                "split": "validation",
                "rows": int(len(validation)),
                **regression_metrics(validation[MULTI_HORIZON_TARGET_COLUMN], validation_predictions),
            }
        )

        refit = pd.concat([train, validation], ignore_index=True)
        model.fit(refit[FEATURE_COLUMNS], refit[MULTI_HORIZON_TARGET_COLUMN])
        test_predictions = model.predict(test[FEATURE_COLUMNS])
        metrics.append(
            {
                "horizon_days": horizon,
                "split": "test_refit_train_validation",
                "rows": int(len(test)),
                **regression_metrics(test[MULTI_HORIZON_TARGET_COLUMN], test_predictions),
            }
        )
        models[str(horizon)] = {
            "model": model,
            "model_name": "linear_regression",
            "feature_columns": FEATURE_COLUMNS,
            "horizon_days": horizon,
            "target_column": MULTI_HORIZON_TARGET_COLUMN,
            "split": split_metadata,
        }

    bundle = {
        "model_type": "direct_multi_horizon",
        "model_name": "linear_regression",
        "horizons_days": list(horizons),
        "max_horizon_days": max(horizons),
        "models": models,
        "feature_columns": FEATURE_COLUMNS,
        "target_definition": "maximum daytime heat index at the requested future calendar-day horizon in Celsius",
        "feature_availability": "selected complete day's observed weather and prior observations only; no future weather inputs",
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    metadata = {
        "model_file": str(model_path),
        "source_daily_file": str(daily_path),
        "model_type": bundle["model_type"],
        "model_name": bundle["model_name"],
        "horizons_days": list(horizons),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": MULTI_HORIZON_TARGET_COLUMN,
        "feature_availability": bundle["feature_availability"],
        "metrics": metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return metadata
