"""Generate HeatSafe exploratory data analysis charts and findings."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EDA_DIR = PROCESSED_DIR / "eda"
os.environ.setdefault("MPLCONFIGDIR", str(PROCESSED_DIR / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns


LOCATION_ORDER = ["Surigao City", "Butuan City", "Davao City"]
HIGH_RISK_CATEGORIES = ["Danger", "Extreme Danger"]
PALETTE = {
    "Surigao City": "#0077b6",
    "Butuan City": "#e76f51",
    "Davao City": "#2a9d8f",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    hourly = pd.read_csv(PROCESSED_DIR / "all_locations_hourly_heat_index.csv")
    daily = pd.read_csv(PROCESSED_DIR / "daily_heat_index.csv")
    hourly["recorded_at"] = pd.to_datetime(hourly["recorded_at"])
    daily["local_date"] = pd.to_datetime(daily["local_date"])
    hourly["year"] = hourly["recorded_at"].dt.year
    hourly["month"] = hourly["recorded_at"].dt.month
    daily["year"] = daily["local_date"].dt.year
    daily["month"] = daily["local_date"].dt.month
    daily["month_name"] = daily["local_date"].dt.strftime("%b")
    return hourly, daily


def save_figure(filename: str) -> str:
    path = EDA_DIR / filename
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return str(path)


def chart_yearly_temperature(hourly: pd.DataFrame) -> str:
    data = (
        hourly[hourly["is_valid_for_analysis"]]
        .groupby(["location_name", "year"], as_index=False)["temperature_2m"]
        .mean()
    )
    plt.figure(figsize=(11, 6))
    sns.lineplot(
        data=data,
        x="year",
        y="temperature_2m",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
        marker="o",
    )
    plt.title("Historical Mean Hourly Temperature by Year")
    plt.xlabel("Year")
    plt.ylabel("Mean temperature (°C)")
    plt.grid(alpha=0.25)
    return save_figure("yearly_temperature_trends.png")


def chart_monthly_average_heat_index(hourly: pd.DataFrame) -> str:
    data = (
        hourly[hourly["is_valid_for_analysis"]]
        .groupby(["location_name", "month"], as_index=False)["heat_index_celsius"]
        .mean()
    )
    plt.figure(figsize=(11, 6))
    sns.lineplot(
        data=data,
        x="month",
        y="heat_index_celsius",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
        marker="o",
    )
    plt.title("Average Hourly Heat Index by Month")
    plt.xlabel("Month")
    plt.ylabel("Average heat index (°C)")
    plt.xticks(range(1, 13))
    plt.grid(alpha=0.25)
    return save_figure("monthly_average_heat_index.png")


def chart_daily_max_heat_index(daily: pd.DataFrame) -> str:
    data = daily[daily["daytime_complete"]].copy()
    plt.figure(figsize=(13, 6))
    sns.lineplot(
        data=data,
        x="local_date",
        y="maximum_daytime_heat_index",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
        linewidth=0.8,
        alpha=0.8,
    )
    plt.title("Daily Maximum Daytime Heat Index (10:00–16:00)")
    plt.xlabel("Date")
    plt.ylabel("Maximum daytime heat index (°C)")
    plt.grid(alpha=0.25)
    return save_figure("daily_max_daytime_heat_index.png")


def chart_max_vs_average(daily: pd.DataFrame) -> str:
    data = daily[daily["daytime_complete"]].copy()
    plt.figure(figsize=(9, 7))
    sns.scatterplot(
        data=data,
        x="average_heat_index",
        y="maximum_hourly_heat_index",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
        alpha=0.35,
        s=16,
    )
    minimum = min(data["average_heat_index"].min(), data["maximum_hourly_heat_index"].min())
    maximum = max(data["average_heat_index"].max(), data["maximum_hourly_heat_index"].max())
    plt.plot([minimum, maximum], [minimum, maximum], linestyle="--", color="black", alpha=0.5)
    plt.title("Daily Maximum versus Average Heat Index")
    plt.xlabel("Average hourly heat index (°C)")
    plt.ylabel("Maximum hourly heat index (°C)")
    return save_figure("maximum_vs_average_heat_index.png")


def chart_temperature_humidity_relationship(hourly: pd.DataFrame) -> str:
    data = hourly[hourly["is_valid_for_analysis"]].copy()
    sample = data.sample(min(15000, len(data)), random_state=42)
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.scatterplot(
        data=sample,
        x="temperature_2m",
        y="relative_humidity_2m",
        hue="heat_index_celsius",
        palette="inferno",
        alpha=0.45,
        s=12,
        legend=False,
        ax=ax,
    )
    norm = plt.Normalize(
        vmin=float(sample["heat_index_celsius"].min()),
        vmax=float(sample["heat_index_celsius"].max()),
    )
    fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap="inferno"),
        ax=ax,
        label="Heat index (°C)",
    )
    plt.title("Temperature and Relative Humidity Relationship")
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Relative humidity (%)")
    return save_figure("temperature_humidity_relationship.png")


def chart_category_distribution(hourly: pd.DataFrame) -> str:
    data = hourly[hourly["is_valid_for_analysis"]].copy()
    categories = ["Not Hazardous", "Caution", "Extreme Caution", "Danger", "Extreme Danger"]
    counts = (
        data.groupby(["location_name", "risk_category"], observed=False)
        .size()
        .reset_index(name="count")
    )
    counts["risk_category"] = pd.Categorical(counts["risk_category"], categories=categories, ordered=True)
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=counts,
        x="risk_category",
        y="count",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
    )
    plt.title("Hourly Heat Index Category Distribution")
    plt.xlabel("PAGASA category")
    plt.ylabel("Valid hourly observations")
    plt.xticks(rotation=20)
    return save_figure("heat_index_category_distribution.png")


def chart_high_risk_days(daily: pd.DataFrame) -> str:
    data = daily[
        daily["daytime_complete"] & daily["daily_risk_category"].isin(HIGH_RISK_CATEGORIES)
    ].copy()
    counts = data.groupby(["location_name", "year"], as_index=False).size()
    counts = counts.rename(columns={"size": "high_risk_days"})
    years = sorted(daily["year"].dropna().unique())
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=counts,
        x="year",
        y="high_risk_days",
        hue="location_name",
        hue_order=LOCATION_ORDER,
        palette=PALETTE,
    )
    plt.title("High-Risk Days by Year (Danger or Extreme Danger)")
    plt.xlabel("Year")
    plt.ylabel("Number of complete daytime high-risk days")
    plt.xticks(range(len(years)), [str(int(year)) for year in years])
    return save_figure("high_risk_days_by_year.png")


def chart_location_comparison(daily: pd.DataFrame) -> str:
    data = daily[daily["daytime_complete"]].copy()
    comparison = (
        data.groupby("location_name", as_index=False)["maximum_daytime_heat_index"]
        .agg(mean="mean", percentile_95=lambda values: values.quantile(0.95))
        .melt(id_vars="location_name", var_name="metric", value_name="heat_index_celsius")
    )
    comparison["metric"] = comparison["metric"].map(
        {"mean": "Mean", "percentile_95": "95th percentile"}
    )
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=comparison,
        x="location_name",
        y="heat_index_celsius",
        hue="metric",
        palette="viridis",
    )
    plt.title("Location Comparison of Daily Peak Daytime Heat Index")
    plt.xlabel("Location")
    plt.ylabel("Heat index (°C)")
    plt.xticks(rotation=15)
    return save_figure("location_comparison.png")


def chart_seasonal_heat_patterns(daily: pd.DataFrame) -> str:
    data = daily[daily["daytime_complete"]].copy()
    pivot = data.pivot_table(
        index="location_name",
        columns="month",
        values="maximum_daytime_heat_index",
        aggfunc="mean",
    ).reindex(LOCATION_ORDER)
    pivot.columns = [str(int(month)) for month in pivot.columns]
    plt.figure(figsize=(12, 4.5))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={"label": "°C"})
    plt.title("Seasonal Pattern of Mean Daily Peak Daytime Heat Index")
    plt.xlabel("Month")
    plt.ylabel("Location")
    return save_figure("seasonal_heat_patterns.png")


def chart_correlations(hourly: pd.DataFrame) -> str:
    columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "wind_speed_10m",
        "precipitation",
        "cloud_cover",
        "shortwave_radiation",
        "heat_index_celsius",
    ]
    correlation = hourly[hourly["is_valid_for_analysis"]][columns].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title("Correlation Matrix of Weather Variables and Heat Index")
    return save_figure("correlation_matrix.png")


def build_findings(hourly: pd.DataFrame, daily: pd.DataFrame) -> dict:
    valid_hourly = hourly[hourly["is_valid_for_analysis"]].copy()
    complete_daily = daily[daily["daytime_complete"]].copy()
    category_counts = (
        valid_hourly.groupby(["location_name", "risk_category"]).size().unstack(fill_value=0)
    )
    high_risk = complete_daily[
        complete_daily["daily_risk_category"].isin(HIGH_RISK_CATEGORIES)
    ]
    correlation = valid_hourly[
        [
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "wind_speed_10m",
            "precipitation",
            "cloud_cover",
            "shortwave_radiation",
            "heat_index_celsius",
        ]
    ].corr()["heat_index_celsius"].drop("heat_index_celsius")

    peak_row = complete_daily.loc[complete_daily["maximum_daytime_heat_index"].idxmax()]
    location_means = (
        complete_daily.groupby("location_name")["maximum_daytime_heat_index"].mean().sort_values(ascending=False)
    )
    monthly_means = (
        complete_daily.groupby(["location_name", "month"])["maximum_daytime_heat_index"]
        .mean()
        .reset_index()
    )
    peak_months = (
        monthly_means.loc[monthly_means.groupby("location_name")["maximum_daytime_heat_index"].idxmax()]
        .set_index("location_name")["month"]
        .astype(int)
        .to_dict()
    )
    high_risk_counts = high_risk.groupby("location_name").size().sort_values(ascending=False)

    return {
        "valid_hourly_record_count": int(len(valid_hourly)),
        "complete_daytime_record_count": int(len(complete_daily)),
        "hourly_category_counts": {
            location: {str(category): int(count) for category, count in row.items()}
            for location, row in category_counts.iterrows()
        },
        "high_risk_day_counts": {location: int(count) for location, count in high_risk_counts.items()},
        "mean_daily_peak_daytime_heat_index_celsius": {
            location: round(float(value), 3) for location, value in location_means.items()
        },
        "peak_month_by_location": peak_months,
        "highest_complete_daytime_peak": {
            "location": peak_row["location_name"],
            "date": peak_row["local_date"].date().isoformat(),
            "heat_index_celsius": round(float(peak_row["maximum_daytime_heat_index"]), 3),
        },
        "heat_index_correlations": {column: round(float(value), 4) for column, value in correlation.items()},
    }


def write_findings_markdown(findings: dict) -> None:
    lines = [
        "# HeatSafe Exploratory Data Analysis Findings",
        "",
        "These findings were generated from the processed HeatSafe dataset. Incomplete days were excluded from daily peak comparisons.",
        "",
        f"- Valid hourly records analyzed: **{findings['valid_hourly_record_count']:,}**",
        f"- Complete daytime daily records analyzed: **{findings['complete_daytime_record_count']:,}**",
        "",
        "## Observed findings",
        "",
        f"- The highest complete daytime heat-index observation was **{findings['highest_complete_daytime_peak']['heat_index_celsius']:.3f}°C** in **{findings['highest_complete_daytime_peak']['location']}** on **{findings['highest_complete_daytime_peak']['date']}**.",
        "- Mean daily peak daytime heat index by location:",
    ]
    for location, value in findings["mean_daily_peak_daytime_heat_index_celsius"].items():
        lines.append(f"  - {location}: **{value:.3f}°C**")
    lines.extend(["", "- High-risk days are defined here as complete daytime days classified as Danger or Extreme Danger:"])
    for location, count in findings["high_risk_day_counts"].items():
        lines.append(f"  - {location}: **{count:,} days**")
    lines.extend(["", "- Month with the highest mean daily peak daytime heat index by location:"])
    for location, month in findings["peak_month_by_location"].items():
        lines.append(f"  - {location}: **month {month}**")
    lines.extend(["", "- Pearson correlations with hourly heat index:"])
    for variable, value in findings["heat_index_correlations"].items():
        lines.append(f"  - {variable}: **{value:.4f}**")
    lines.extend([
        "",
        "These are descriptive relationships in the collected modeled/reanalysis dataset. They do not establish causation and should not be interpreted as medical or official warning guidance.",
    ])
    (EDA_DIR / "eda_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eda() -> dict:
    EDA_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    hourly, daily = load_data()
    chart_files = [
        chart_yearly_temperature(hourly),
        chart_monthly_average_heat_index(hourly),
        chart_daily_max_heat_index(daily),
        chart_max_vs_average(daily),
        chart_temperature_humidity_relationship(hourly),
        chart_category_distribution(hourly),
        chart_high_risk_days(daily),
        chart_location_comparison(daily),
        chart_seasonal_heat_patterns(daily),
        chart_correlations(hourly),
    ]
    findings = build_findings(hourly, daily)
    findings["chart_files"] = chart_files
    (EDA_DIR / "eda_summary.json").write_text(
        json.dumps(findings, indent=2, default=str), encoding="utf-8"
    )
    write_findings_markdown(findings)
    return findings
