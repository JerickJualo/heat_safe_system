# Dataset and Heat-Index Methodology

## Source

Historical hourly weather data is collected programmatically from the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) using the ERA5 model. The source is modeled/reanalysis data, not direct observations from a local weather station.

Locations:

- Surigao City, Surigao del Norte
- Butuan City, Agusan del Norte
- Davao City

Timezone: `Asia/Manila`.

## Coverage policy

- Complete requested years: January 1, 2017 through December 31, 2025.
- 2026: partial year only, ending at the latest non-null timestamp returned by the API.
- The collector does not request future dates and does not fill unavailable 2026 values.
- Trailing nulls are retained and flagged so model-update delay is visible.

## Collected variables

The hourly dataset contains temperature, relative humidity, dew point, wind speed, precipitation, cloud cover, and shortwave radiation, together with location, local timestamp, source/model metadata, and quality information.

## Cleaning and validation

The preprocessing pipeline:

1. Parses timestamps and converts them to timezone-aware `Asia/Manila` values.
2. Coerces numeric fields and flags missing required inputs.
3. Checks physical ranges and duplicate timestamps.
4. Preserves invalid/incomplete rows with explicit quality flags.
5. Calculates heat index only for valid required inputs.
6. Aggregates daily summaries without fabricating missing hours.

## Heat index

The implementation follows the National Weather Service approach:

- simple heat-index formula below the regression threshold;
- Rothfusz regression for the main range;
- documented low-relative-humidity and high-relative-humidity adjustments;
- conversion between Celsius and Fahrenheit handled explicitly.

PAGASA classification applied to Celsius heat index:

| Heat index | Category |
|---:|---|
| `< 27` | Not Hazardous |
| `27–32` | Caution |
| `33–41` | Extreme Caution |
| `42–51` | Danger |
| `>= 52` | Extreme Danger |

## Daily window

Daytime maximum heat index is the maximum valid hourly heat index from 10:00 through 16:00 inclusive in `Asia/Manila`. A complete daytime summary requires seven valid daytime hours; a complete daily summary requires 24 valid hours.
