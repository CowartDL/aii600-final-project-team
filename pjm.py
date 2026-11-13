"""Load, check, and clean the PJM data. The notebook and the model code import this."""

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

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

# Fit on days before VALID_START, choose on the validation year, and score
# once on days from HELD_OUT_START. See decisions.md, 2026-11-13.
VALID_START = pd.Timestamp("2024-01-01")
HELD_OUT_START = pd.Timestamp("2025-01-01")

# Assumed costs per MWh of the peak hour until PJM's prices arrive.
# See decisions.md, 2026-11-13.
COST_SHORT = 50.0  # c_u: buying a missing MWh in real time
COST_LONG = 10.0   # c_o: reselling an unneeded MWh in real time

# Peak demand (GW) above which each extra GW of PJM's forecast gets its own slope.
KNOT_GW = 110.0


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


def add_known_the_day_before(days):
    """Add what a buyer knows on the morning before day D: the peak and PJM's miss on day D-2."""
    days = days.copy()
    days["peak_lag2_mw"] = days["peak_mw"].shift(2)
    days["forecast_miss_lag2_mw"] = (days["peak_mw"] - days["forecast_peak_mw"]).shift(2)
    return days.dropna(subset=["peak_mw", "forecast_peak_mw", "peak_lag2_mw", "forecast_miss_lag2_mw"])


def split(days):
    """Training, validation, and held-out days, by date."""
    train = days[days.index < VALID_START]
    valid = days[(days.index >= VALID_START) & (days.index < HELD_OUT_START)]
    held_out = days[days.index >= HELD_OUT_START]
    return train, valid, held_out


def critical_fractile(cost_short=COST_SHORT, cost_long=COST_LONG):
    """The quantile of tomorrow's peak that minimizes the expected cost."""
    return cost_short / (cost_short + cost_long)


def cost(bought_mw, peak_mw, cost_short=COST_SHORT, cost_long=COST_LONG):
    """Dollars lost on the peak hour: real-time premium on a shortfall, resale loss on a surplus."""
    short = np.maximum(peak_mw - bought_mw, 0)
    long = np.maximum(bought_mw - peak_mw, 0)
    return cost_short * short + cost_long * long


def design(days):
    """Model inputs in GW: intercept, PJM's forecast, its excess over KNOT_GW, weekend, PJM's miss two days before."""
    forecast_gw = days["forecast_peak_mw"].to_numpy() / 1000
    return np.column_stack([
        np.ones(len(days)),
        forecast_gw,
        np.maximum(forecast_gw - KNOT_GW, 0),
        (days["weekday"] >= 5).to_numpy(float),
        days["forecast_miss_lag2_mw"].to_numpy() / 1000,
    ])


def fit_quantile(X, y, tau):
    """Linear quantile regression by linear programming: minimize the pinball loss at tau."""
    n, p = X.shape
    objective = np.concatenate([np.zeros(p), np.full(n, tau), np.full(n, 1 - tau)])
    constraints = np.hstack([X, np.eye(n), -np.eye(n)])
    bounds = [(None, None)] * p + [(0, None)] * (2 * n)
    result = linprog(objective, A_eq=constraints, b_eq=y, bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(result.message)
    return result.x[:p]
