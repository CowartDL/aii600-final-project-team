"""Load, check, and clean the PJM data. The notebook and the model code import this."""

import hashlib
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# EIA-930's PJM forecast covers about a third of PJM's load in July 2015,
# its first month, so the analysis starts with the first whole year after.
ANALYSIS_START = pd.Timestamp("2016-01-01")

# An hour more than this far from the median of the five hours around it is a
# reporting error, not load. This flags 9 demand hours in 2015-2026.
SPIKE = 0.15

# A day with fewer valid hours than this has no peak.
MIN_HOURS = 20


def check_data():
    """Compare each file in data/ with the SHA-256 listed in data/README.md."""
    readme = (DATA / "README.md").read_text(encoding="utf-8")
    expected = dict(re.findall(r"`([\w.-]+\.csv)`.*?`([0-9a-f]{64})`", readme))
    if not expected:
        raise ValueError("data/README.md lists no SHA-256")
    for name, digest in expected.items():
        actual = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"{name}: SHA-256 {actual} does not match data/README.md")
    return expected


def flag_spikes(series):
    """True where an hour is more than SPIKE from the 5-hour centered median."""
    median = series.rolling(5, center=True, min_periods=3).median()
    return (series / median - 1).abs() > SPIKE


def load_hourly():
    """Hourly PJM demand and PJM's day-ahead forecast, MW, with spikes set to NaN."""
    hourly = pd.read_csv(DATA / "pjm_hourly.csv", parse_dates=["date", "utc_end"])
    hourly["demand_spike"] = flag_spikes(hourly["demand_adjusted_mw"])
    hourly["forecast_spike"] = flag_spikes(hourly["forecast_mw"])
    hourly["demand_clean_mw"] = hourly["demand_adjusted_mw"].mask(hourly["demand_spike"])
    hourly["forecast_clean_mw"] = hourly["forecast_mw"].mask(hourly["forecast_spike"])
    return hourly


def load_weather():
    """Daily high and low, deg C, averaged over the five stations."""
    weather = pd.read_csv(DATA / "weather_daily.csv", parse_dates=["date"])
    return weather.groupby("date")[["tmax_c", "tmin_c"]].mean()


def daily(hourly, weather):
    """One row per local date from ANALYSIS_START: the peak, PJM's forecast of it, and temperature."""
    days = hourly.groupby("date").agg(
        peak_mw=("demand_clean_mw", "max"),
        forecast_peak_mw=("forecast_clean_mw", "max"),
        valid_hours=("demand_clean_mw", "count"),
        forecast_hours=("forecast_clean_mw", "count"),
    )
    days.loc[days["valid_hours"] < MIN_HOURS, "peak_mw"] = float("nan")
    days.loc[days["forecast_hours"] < MIN_HOURS, "forecast_peak_mw"] = float("nan")
    days = days.join(weather)
    days["weekday"] = days.index.dayofweek  # Monday is 0
    return days[days.index >= ANALYSIS_START]
