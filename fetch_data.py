"""Build the data files the notebook reads, from the public sources.

    python -I fetch_data.py

Downloads EIA-930 six-month balance files and NOAA GHCN-Daily station files
into data/raw/ (skipped when already there), then writes

    data/pjm_hourly.csv     PJM hourly demand and PJM's day-ahead forecast, MW
    data/weather_daily.csv  daily high and low temperature, deg C, five stations

and prints the SHA-256 of each. EIA revises recent months, so a rebuild can
differ from the files on the `data` release. The notebook reads the release.
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

START = pd.Timestamp("2015-07-01")
END = pd.Timestamp("2026-10-31")  # last local date kept

EIA_URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_{year}_{half}.csv"
NOAA_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{station}.csv.gz"
USER_AGENT = "aii600-course-project"

# Columns kept from EIA-930, and their names in data/pjm_hourly.csv.
EIA_COLUMNS = {
    "Data Date": "date",
    "Hour Number": "hour",
    "UTC Time at End of Hour": "utc_end",
    "Demand Forecast (MW)": "forecast_mw",
    "Demand (MW)": "demand_mw",
    "Demand (MW) (Imputed)": "demand_imputed_mw",
    "Demand (MW) (Adjusted)": "demand_adjusted_mw",
}

# Airports near PJM's largest load centers.
STATIONS = {
    "USW00013739": "PHL",  # Philadelphia
    "USW00013743": "DCA",  # Washington Reagan
    "USW00094823": "PIT",  # Pittsburgh
    "USW00014821": "CMH",  # Columbus
    "USW00094846": "ORD",  # Chicago O'Hare
}


def download(url, path):
    if path.exists():
        return
    print(f"downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(response.read())
        tmp.rename(path)


def half_years():
    year, half = START.year, "Jan_Jun" if START.month <= 6 else "Jul_Dec"
    while pd.Timestamp(f"{year}-{'01' if half == 'Jan_Jun' else '07'}-01") <= END:
        yield year, half
        year, half = (year, "Jul_Dec") if half == "Jan_Jun" else (year + 1, "Jan_Jun")


def pjm_hourly():
    parts = []
    for year, half in half_years():
        path = RAW / f"EIA930_BALANCE_{year}_{half}.csv"
        download(EIA_URL.format(year=year, half=half), path)
        frame = pd.read_csv(
            path,
            usecols=lambda c: c == "Balancing Authority" or c in EIA_COLUMNS,
            dtype=str,
        )
        frame = frame[frame["Balancing Authority"] == "PJM"].drop(columns="Balancing Authority")
        missing = set(EIA_COLUMNS) - set(frame.columns)
        if missing:
            print(f"  {path.name}: no column {sorted(missing)}; left empty")
        parts.append(frame.reindex(columns=list(EIA_COLUMNS)))

    hourly = pd.concat(parts, ignore_index=True).rename(columns=EIA_COLUMNS)
    hourly["date"] = pd.to_datetime(hourly["date"], format="%m/%d/%Y")
    hourly["hour"] = hourly["hour"].astype(int)
    hourly["utc_end"] = pd.to_datetime(hourly["utc_end"], format="%m/%d/%Y %I:%M:%S %p")
    for column in hourly.columns[3:]:
        hourly[column] = pd.to_numeric(hourly[column].str.replace(",", ""), errors="coerce")
    hourly = hourly[hourly["date"].between(START, END)]
    return hourly.drop_duplicates("utc_end").sort_values("utc_end")


def weather_daily():
    rows = []
    for station, name in STATIONS.items():
        path = RAW / f"{station}.csv.gz"
        download(NOAA_URL.format(station=station), path)
        frame = pd.read_csv(
            path,
            header=None,
            names=["id", "date", "element", "value", "mflag", "qflag", "sflag", "obs_time"],
            dtype=str,
        )
        # Keep the daily high and low that passed NOAA's quality checks.
        frame = frame[frame["element"].isin(["TMAX", "TMIN"]) & frame["qflag"].isna()]
        frame["date"] = pd.to_datetime(frame["date"], format="%Y%m%d")
        frame = frame[frame["date"].between(START, END)]
        frame["value"] = frame["value"].astype(int) / 10  # tenths of a degree C
        wide = frame.pivot(index="date", columns="element", values="value").reset_index()
        wide.insert(1, "station", name)
        rows.append(wide.rename(columns={"TMAX": "tmax_c", "TMIN": "tmin_c"}))
    weather = pd.concat(rows, ignore_index=True)
    weather.columns.name = None
    return weather.sort_values(["date", "station"])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    outputs = {
        OUT / "pjm_hourly.csv": pjm_hourly(),
        OUT / "weather_daily.csv": weather_daily(),
    }
    for path, frame in outputs.items():
        frame.to_csv(path, index=False, lineterminator="\n")
        print(f"{path.relative_to(ROOT).as_posix()}  {len(frame)} rows  sha256 {sha256(path)}")


if __name__ == "__main__":
    sys.exit(main())
