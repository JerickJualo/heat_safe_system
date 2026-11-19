# Machine-Learning Methodology

## Next-day objective

Predict the next calendar day's maximum daytime heat index in degrees Celsius for each location.

## Feature construction

Features use information available on the current feature date and earlier dates:

- current-day temperature, humidity, wind, precipitation, cloud, radiation, and heat-index summaries;
- one- and two-day heat-index lags;
- previous-only three-day and seven-day rolling means;
- month and day-of-year sine/cosine seasonality;
- location name as a categorical feature.

Rolling statistics are shifted before aggregation so the current target or future observations cannot enter the feature value.

## Models and evaluation

The pipeline evaluates:

- persistence baseline;
- Linear Regression;
- Random Forest Regressor;
- HistGradientBoosting Regressor.

Data is split chronologically by target date into training, validation, and held-out test partitions. The selected model is chosen using validation MAE, then refit on training plus validation data before final test evaluation.

## Verified result

Linear Regression was selected. The verified held-out test results were:

| Metric | Result |
|---|---:|
| MAE | 1.2497°C |
| RMSE | 1.6527°C |
| R² | 0.6045 |

The saved artifact is `models/phase4/heat_index_next_day_model.joblib`. Running the Django application or generating predictions does not retrain the model. Retraining occurs only when `scripts/train_heat_index_model.py` is explicitly executed.

## Five-day direct forecast extension

The prediction page supports horizons 1 through 5 using direct models saved in `models/phase4/heat_index_multi_horizon_model.joblib`. One Linear Regression model is trained separately for each horizon. The target for horizon `h` is the maximum daytime heat index exactly `h` calendar days after the selected feature date.

The five-day models use the same leakage-aware current-day, lag, rolling, seasonal, and location features. They do not recursively insert predicted values as if they were observations, and they do not require future weather inputs. The extension is trained with:

```powershell
.\.venv\Scripts\python.exe scripts\train_multi_horizon_model.py
```

The direct-model validation and held-out test metrics are stored in `data/processed/ml/multi_horizon_model_metadata.json`. Expected error generally increases with forecast horizon, so the five-day estimates should be interpreted as broader decision-support guidance rather than precise official forecasts.

## Interpretation limits

The prediction is a decision-support estimate based on historical reanalysis-derived features. It is not an official forecast or PAGASA warning and should not replace official advisories.
