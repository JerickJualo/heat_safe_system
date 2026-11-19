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
