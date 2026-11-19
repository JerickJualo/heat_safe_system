# Machine-Learning Methodology

## Objective

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

## Interpretation limits

The prediction is a decision-support estimate based on historical reanalysis-derived features. It is not an official forecast or PAGASA warning and should not replace official advisories.
