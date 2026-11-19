"""Model construction and regression evaluation helpers."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .features import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", "passthrough", NUMERIC_FEATURES),
            ("location", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def build_candidate_models(random_state: int = 42) -> dict[str, Pipeline]:
    return {
        "linear_regression": Pipeline(
            [("preprocess", make_preprocessor()), ("model", LinearRegression())]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=200,
                        min_samples_leaf=2,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=300,
                        learning_rate=0.05,
                        max_leaf_nodes=31,
                        l2_regularization=0.1,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }


def persistence_predictions(frame: pd.DataFrame) -> np.ndarray:
    """Predict tomorrow with today's observed maximum daytime heat index."""
    return frame["maximum_daytime_heat_index"].to_numpy(dtype=float)


def regression_metrics(y_true: Iterable[float], predictions: Iterable[float]) -> dict[str, float]:
    actual = np.asarray(list(y_true), dtype=float)
    predicted = np.asarray(list(predictions), dtype=float)
    if len(actual) != len(predicted) or len(actual) == 0:
        raise ValueError("Actual and predicted arrays must have equal non-zero lengths.")
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }
