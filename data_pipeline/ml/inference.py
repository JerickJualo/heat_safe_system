"""Reusable next-day heat-index inference."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from .features import FEATURE_COLUMNS, build_feature_frame


def load_model_bundle(model_path: Path) -> dict:
    bundle = joblib.load(model_path)
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise ValueError("Saved model artifact does not contain a valid model bundle.")
    return bundle


def prepare_next_day_features(history: pd.DataFrame) -> pd.DataFrame:
    """Prepare the latest complete day's features for a next-day forecast."""
    engineered = build_feature_frame(history)
    usable = engineered.dropna(subset=FEATURE_COLUMNS)
    if usable.empty:
        raise ValueError("History does not contain enough complete consecutive days for inference.")
    latest = usable.sort_values("feature_date").tail(1).copy()
    return latest


def predict_next_day_maximum_daytime_heat_index(model_path: Path, history: pd.DataFrame) -> float:
    return predict_with_model_bundle(load_model_bundle(model_path), history)


def predict_with_model_bundle(bundle: dict, history: pd.DataFrame) -> float:
    """Predict from an already-loaded bundle to avoid repeated disk loads."""
    if not isinstance(bundle, dict) or "model" not in bundle or "feature_columns" not in bundle:
        raise ValueError("Saved model artifact does not contain a usable model bundle.")
    features = prepare_next_day_features(history)
    feature_columns = bundle["feature_columns"]
    prediction = bundle["model"].predict(features[feature_columns])
    value = float(prediction[0])
    if not pd.notna(value):
        raise ValueError("Model returned a non-numeric prediction.")
    return value


def load_multi_horizon_bundle(model_path: Path) -> dict:
    bundle = joblib.load(model_path)
    if (
        not isinstance(bundle, dict)
        or bundle.get("model_type") != "direct_multi_horizon"
        or not isinstance(bundle.get("models"), dict)
    ):
        raise ValueError("Saved artifact is not a valid direct multi-horizon model bundle.")
    return bundle


def prepare_features_for_feature_date(history: pd.DataFrame, feature_date) -> pd.DataFrame:
    """Prepare model inputs for a selected complete feature date."""
    target_date = pd.Timestamp(feature_date).normalize()
    frame = history.copy()
    frame["local_date"] = pd.to_datetime(frame["local_date"], errors="coerce")
    frame = frame[frame["local_date"] <= target_date]
    engineered = build_feature_frame(frame)
    selected = engineered[engineered["feature_date"] == target_date].copy()
    if selected.empty:
        raise ValueError(
            "The selected feature date is unavailable or does not have enough complete prior observations."
        )
    feature_columns = FEATURE_COLUMNS
    selected = selected.dropna(subset=feature_columns)
    if selected.empty:
        raise ValueError("The selected feature date does not contain complete model inputs.")
    return selected.tail(1)


def latest_complete_feature_date(history: pd.DataFrame):
    """Return the latest date with complete model inputs available."""
    engineered = build_feature_frame(history)
    usable = engineered.dropna(subset=FEATURE_COLUMNS)
    if usable.empty:
        raise ValueError("History does not contain enough complete observations for inference.")
    return usable["feature_date"].max().date()


def predict_multi_horizon_with_bundle(
    bundle: dict,
    history: pd.DataFrame,
    feature_date,
    max_horizon_days: int = 5,
) -> list[dict]:
    """Predict direct horizons one through ``max_horizon_days``."""
    if not 1 <= max_horizon_days <= 5:
        raise ValueError("max_horizon_days must be between 1 and 5.")
    if not isinstance(bundle, dict) or bundle.get("model_type") != "direct_multi_horizon":
        raise ValueError("A direct multi-horizon model bundle is required.")
    feature_date_value = (
        latest_complete_feature_date(history)
        if feature_date is None
        else pd.Timestamp(feature_date).date()
    )
    row = prepare_features_for_feature_date(history, feature_date_value)
    results = []
    for horizon in range(1, max_horizon_days + 1):
        model_entry = bundle["models"].get(str(horizon))
        if not model_entry:
            raise ValueError(f"No trained model is available for horizon {horizon}.")
        prediction = model_entry["model"].predict(row[model_entry["feature_columns"]])
        value = float(prediction[0])
        if not pd.notna(value):
            raise ValueError(f"Model returned a non-numeric prediction for horizon {horizon}.")
        results.append(
            {
                "horizon_days": horizon,
                "feature_date": feature_date_value.isoformat(),
                "target_date": (pd.Timestamp(feature_date_value) + pd.Timedelta(days=horizon)).date().isoformat(),
                "predicted_heat_index_celsius": value,
                "model_name": model_entry["model_name"],
            }
        )
    return results
