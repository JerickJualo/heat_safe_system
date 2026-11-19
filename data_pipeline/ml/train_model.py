"""Train and evaluate HeatSafe next-day maximum daytime heat-index models."""

from __future__ import annotations

import json
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(_PROJECT_ROOT / "data" / "processed" / ".matplotlib"))

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .evaluation import build_candidate_models, persistence_predictions, regression_metrics
from .features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    assert_no_target_leakage,
    build_ml_dataset,
    split_by_target_date,
)


PROJECT_ROOT = _PROJECT_ROOT
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ML_DIR = PROCESSED_DIR / "ml"
MODEL_DIR = PROJECT_ROOT / "models" / "phase4"
DAILY_PATH = PROCESSED_DIR / "daily_heat_index.csv"
MODEL_PATH = MODEL_DIR / "heat_index_next_day_model.joblib"


def _metrics_row(model_name: str, split_name: str, y_true: pd.Series, predictions: np.ndarray) -> dict:
    metrics = regression_metrics(y_true, predictions)
    return {
        "model": model_name,
        "split": split_name,
        "rows": int(len(y_true)),
        **metrics,
    }


def _save_prediction_chart(predictions: pd.DataFrame) -> str:
    path = ML_DIR / "actual_vs_predicted_selected_model.png"
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    for axis, location in zip(axes, ["Surigao City", "Butuan City", "Davao City"]):
        data = predictions[predictions["location_name"] == location].sort_values("target_date")
        axis.plot(data["target_date"], data["actual"], label="Actual", linewidth=1.0)
        axis.plot(data["target_date"], data["predicted"], label="Predicted", linewidth=0.9, alpha=0.8)
        axis.set_title(location)
        axis.set_ylabel("Heat index (deg C)")
        axis.grid(alpha=0.25)
        axis.legend(loc="upper right")
    axes[-1].set_xlabel("Target date")
    fig.suptitle("Actual versus Predicted Next-Day Maximum Daytime Heat Index")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _save_model_comparison_chart(metrics: pd.DataFrame) -> str:
    path = ML_DIR / "model_comparison_metrics.png"
    validation = metrics[metrics["split"] == "validation"].copy()
    long = validation.melt(
        id_vars="model", value_vars=["mae", "rmse"], var_name="metric", value_name="value"
    )
    fig, axis = plt.subplots(figsize=(10, 6))
    sns.barplot(data=long, x="model", y="value", hue="metric", ax=axis, palette="viridis")
    axis.set_title("Validation MAE and RMSE by Model")
    axis.set_xlabel("Model")
    axis.set_ylabel("Error (deg C)")
    axis.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def run_training() -> dict:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    daily = pd.read_csv(DAILY_PATH)
    dataset = build_ml_dataset(daily)
    dataset_path = ML_DIR / "ml_dataset.csv"
    dataset.to_csv(dataset_path, index=False, encoding="utf-8")

    assert_no_target_leakage(FEATURE_COLUMNS)
    train, validation, test, split_metadata = split_by_target_date(dataset)
    x_train, y_train = train[FEATURE_COLUMNS], train[TARGET_COLUMN]
    x_validation, y_validation = validation[FEATURE_COLUMNS], validation[TARGET_COLUMN]
    x_test, y_test = test[FEATURE_COLUMNS], test[TARGET_COLUMN]

    metrics_rows = []
    trained_models = {}
    baseline_sets = {
        "validation": (validation, y_validation),
        "test": (test, y_test),
    }
    for split_name, (split_frame, split_target) in baseline_sets.items():
        metrics_rows.append(
            _metrics_row("persistence_baseline", split_name, split_target, persistence_predictions(split_frame))
        )

    for model_name, model in build_candidate_models().items():
        model.fit(x_train, y_train)
        trained_models[model_name] = model
        metrics_rows.append(
            _metrics_row(model_name, "validation", y_validation, model.predict(x_validation))
        )

    validation_rows = [row for row in metrics_rows if row["split"] == "validation"]
    selected_model_name = min(
        (row for row in validation_rows if row["model"] != "persistence_baseline"),
        key=lambda row: (row["mae"], row["rmse"], -row["r2"]),
    )["model"]

    refit_frame = pd.concat([train, validation], ignore_index=True)
    selected_model = build_candidate_models()[selected_model_name]
    selected_model.fit(refit_frame[FEATURE_COLUMNS], refit_frame[TARGET_COLUMN])
    selected_test_predictions = selected_model.predict(x_test)
    metrics_rows.append(_metrics_row(selected_model_name, "test_refit_train_validation", y_test, selected_test_predictions))

    metrics = pd.DataFrame(metrics_rows)
    metrics_path = ML_DIR / "model_comparison.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8")

    prediction_frame = test[["target_date", "location_name"]].copy()
    prediction_frame["actual"] = y_test.to_numpy()
    prediction_frame["predicted"] = selected_test_predictions
    prediction_frame["absolute_error"] = (prediction_frame["actual"] - prediction_frame["predicted"]).abs()
    predictions_path = ML_DIR / "selected_model_test_predictions.csv"
    prediction_frame.to_csv(predictions_path, index=False, encoding="utf-8")

    model_bundle = {
        "model": selected_model,
        "model_name": selected_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target_column": TARGET_COLUMN,
        "forecast_horizon_days": 1,
        "target_definition": "next calendar day's maximum daytime heat index in Celsius",
        "feature_availability": "features use the current complete day's observed weather and prior observations only",
    }
    joblib.dump(model_bundle, MODEL_PATH)

    chart_paths = {
        "actual_vs_predicted": _save_prediction_chart(prediction_frame),
        "model_comparison": _save_model_comparison_chart(metrics),
    }

    test_prediction_min = float(np.min(selected_test_predictions))
    test_prediction_max = float(np.max(selected_test_predictions))
    metadata = {
        "source_daily_file": str(DAILY_PATH),
        "dataset_file": str(dataset_path),
        "model_file": str(MODEL_PATH),
        "model_comparison_file": str(metrics_path),
        "predictions_file": str(predictions_path),
        "selected_model": selected_model_name,
        "target": {
            "column": TARGET_COLUMN,
            "definition": "next calendar day's maximum daytime heat index in Celsius",
            "forecast_horizon_days": 1,
        },
        "feature_columns": FEATURE_COLUMNS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "leakage_checks": {
            "target_column_excluded_from_features": TARGET_COLUMN not in FEATURE_COLUMNS,
            "target_date_excluded_from_features": "target_date" not in FEATURE_COLUMNS,
            "rolling_features_use_shifted_observations": True,
            "chronological_split": True,
        },
        "dataset_rows": int(len(dataset)),
        "locations": sorted(dataset["location_name"].unique().tolist()),
        "split": split_metadata,
        "metrics": metrics.to_dict(orient="records"),
        "selected_test_prediction_range_celsius": {
            "minimum": test_prediction_min,
            "maximum": test_prediction_max,
            "within_reasonable_0_to_80_range": 0.0 <= test_prediction_min <= test_prediction_max <= 80.0,
        },
        "charts": chart_paths,
    }
    metadata_path = ML_DIR / "model_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return metadata


def main() -> int:
    metadata = run_training()
    print(json.dumps(metadata, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
