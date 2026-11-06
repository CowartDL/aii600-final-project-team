# Data

The files the notebook reads are not committed. They are assets on the GitHub release tagged `data`. On another machine, from the project root:

```bash
gh release download data --dir data --repo CowartDL/aii600-final-project-team
```

## Sources and terms

- **PJM hourly demand and PJM's day-ahead demand forecast**: U.S. Energy Information Administration, Hourly Electric Grid Monitor, form EIA-930, six-month balance files at https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/. U.S. government data, in the public domain, so the files can be republished on the release.
- **Daily high and low temperature**: NOAA National Centers for Environmental Information, Global Historical Climatology Network Daily, station files at https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/. U.S. government data, in the public domain.

`fetch_data.py` rebuilds both files from those sources. It needs no account or key:

```bash
python -I fetch_data.py
```

It downloads about 1 GB into `data/raw/` and keeps only PJM's rows. EIA revises recent months, so a rebuild can differ from the release, and its SHA-256 will not match. The notebook reads the release.

## Files

- `pjm_hourly.csv`, SHA-256 `864b6b11d2b5e30e866b009302411c9e94c6017f2a95fe28cdc80947daa1be0b`. One row per hour of PJM demand. 99,384 rows, 1 July 2015 to 31 October 2026, local (Eastern) dates. Columns: `date` and `hour` (the local date and hour number, 1 to 24, 23 or 25 at the clock change), `utc_end` (end of the hour, UTC), `forecast_mw` (PJM's day-ahead forecast), `demand_mw` (as reported), `demand_imputed_mw` (EIA's fill-in where PJM did not report, 244 hours), and `demand_adjusted_mw` (EIA's cleaned series, which the analysis uses).
- `weather_daily.csv`, SHA-256 `e658984bb0f20196d08fb35bdb60c6d666d79733b02a1ec9839e687f8fb8d7fb`. One row per station per day. 20,705 rows, 4,141 days at each of five airports: Philadelphia (`PHL`, USW00013739), Washington Reagan (`DCA`, USW00013743), Pittsburgh (`PIT`, USW00094823), Columbus (`CMH`, USW00014821), and Chicago O'Hare (`ORD`, USW00094846). Columns: `date`, `station`, `tmax_c` and `tmin_c` (deg C). Values that failed NOAA's quality checks are dropped. None are missing in this span.

## Known problems, handled in `pjm.py`

- `demand_mw` holds a placeholder of 2,147,480,000 MW in some hours. `demand_adjusted_mw` replaces it.
- `demand_adjusted_mw` still has single-hour spikes, for example 224 GW on 13 July 2020 against a record near 165 GW. Hours more than 15% from the median of the five around them are set to missing: 9 hours.
- In July 2015, EIA-930's first month, `forecast_mw` is about a third of demand in every hour. The analysis starts on 1 January 2016.
