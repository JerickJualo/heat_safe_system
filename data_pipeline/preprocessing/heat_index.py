"""NWS heat-index calculation and PAGASA risk classification."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


NWS_HEAT_INDEX_REFERENCE = "https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml"
PAGASA_HEAT_INDEX_REFERENCE = "https://www.panahon.gov.ph/heat_index.html"


def celsius_to_fahrenheit(temperature_celsius: float) -> float:
    return temperature_celsius * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(temperature_fahrenheit: float) -> float:
    return (temperature_fahrenheit - 32.0) * 5.0 / 9.0


def _validate_inputs(temperature_celsius: Any, relative_humidity: Any) -> tuple[float, float] | None:
    try:
        temperature = float(temperature_celsius)
        humidity = float(relative_humidity)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(temperature) or not math.isfinite(humidity):
        return None
    if temperature < -60.0 or temperature > 60.0:
        return None
    if humidity < 0.0 or humidity > 100.0:
        return None
    return temperature, humidity


def calculate_heat_index_fahrenheit(temperature_fahrenheit: float, relative_humidity: float) -> float:
    """Calculate heat index in Fahrenheit using the full NWS procedure."""
    temperature = float(temperature_fahrenheit)
    humidity = float(relative_humidity)

    simple = 0.5 * (
        temperature
        + 61.0
        + ((temperature - 68.0) * 1.2)
        + (humidity * 0.094)
    )
    simple_average = 0.5 * (simple + temperature)
    if simple_average < 80.0:
        return simple_average

    heat_index = (
        -42.379
        + 2.04901523 * temperature
        + 10.14333127 * humidity
        - 0.22475541 * temperature * humidity
        - 0.00683783 * temperature**2
        - 0.05481717 * humidity**2
        + 0.00122874 * temperature**2 * humidity
        + 0.00085282 * temperature * humidity**2
        - 0.00000199 * temperature**2 * humidity**2
    )

    if humidity < 13.0 and 80.0 <= temperature <= 112.0:
        adjustment = ((13.0 - humidity) / 4.0) * math.sqrt(
            (17.0 - abs(temperature - 95.0)) / 17.0
        )
        heat_index -= adjustment
    elif humidity > 85.0 and 80.0 <= temperature <= 87.0:
        adjustment = ((humidity - 85.0) / 10.0) * ((87.0 - temperature) / 5.0)
        heat_index += adjustment

    return heat_index


def calculate_heat_index_celsius(temperature_celsius: Any, relative_humidity: Any) -> float:
    """Return NWS heat index in Celsius, or NaN for invalid inputs."""
    validated = _validate_inputs(temperature_celsius, relative_humidity)
    if validated is None:
        return float("nan")
    temperature, humidity = validated
    heat_index_fahrenheit = calculate_heat_index_fahrenheit(
        celsius_to_fahrenheit(temperature), humidity
    )
    return fahrenheit_to_celsius(heat_index_fahrenheit)


def calculate_heat_index_series(
    temperature_celsius: pd.Series, relative_humidity: pd.Series
) -> pd.Series:
    """Vectorized-friendly heat-index calculation for pandas columns."""
    values = [
        calculate_heat_index_celsius(temperature, humidity)
        for temperature, humidity in zip(temperature_celsius, relative_humidity)
    ]
    return pd.Series(values, index=temperature_celsius.index, dtype="float64")


def classify_heat_index(heat_index_celsius: Any) -> str | None:
    """Apply the centralized DOST-PAGASA heat-index categories."""
    try:
        value = float(heat_index_celsius)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    if value < 27.0:
        return "Not Hazardous"
    if value < 33.0:
        return "Caution"
    if value < 42.0:
        return "Extreme Caution"
    if value < 52.0:
        return "Danger"
    return "Extreme Danger"


def classify_heat_index_series(heat_index: pd.Series) -> pd.Series:
    return heat_index.map(classify_heat_index).astype("string")
