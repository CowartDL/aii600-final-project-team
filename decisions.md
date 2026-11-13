# Decisions

This file is the history of the project. Append an entry when a choice changes the work: the quantity, the data, the split, the model, the loss, or the action. Leave old entries in place. A later entry can reverse an earlier one. If a result depends on a random draw, record the seed under Why. The split entry records the cutoff date, or the seed and the fraction. The pull request that merges the code names this entry.

## YYYY-MM-DD: short title

- Decision. What you chose.
- Why. The evidence.
- Alternative. What you rejected.
- Revisit. What would change the choice.

## 2026-10-30: Forecast PJM's next-day peak demand for a day-ahead purchase

- Decision. The quantity is PJM's peak hourly demand on the next day, in MW, from EIA-930. The decision is how many MW a load-serving utility buys in the day-ahead market, and the loss is a newsvendor cost with the real-time price as the penalty on either side.
- Why. EIA-930 has more than ten years of hourly PJM demand in the public domain, so the data can be republished and the held-out set can be a later period. The same series includes PJM's own day-ahead forecast, which is a strong baseline. The cost of a wrong forecast is lopsided, which is the case where buying a quantile instead of the point forecast pays off.
- Alternative. We set aside forecasting daily departures at a busy Capital Bikeshare station to decide how many bikes to stage overnight. Its loss is a clean newsvendor too, but one station's counts are small and noisy, and rebalancing costs are not published. We also considered ERCOT instead of PJM and chose PJM for its larger, steadier load and its published day-ahead and real-time prices.
- Revisit. If PJM's price data cannot be obtained or used, the loss uses stated assumed costs with a sensitivity range. If EIA-930's PJM series has long gaps, we shorten the time span.

## 2026-11-06: Data sources, cleaning rule, and the start of the analysis

- Decision. Demand and PJM's day-ahead forecast come from EIA-930's six-month balance files, kept as `data/pjm_hourly.csv` (1 July 2015 to 31 October 2026, 99,384 hours). Temperature is the mean daily high and low at five airports near PJM's largest loads (Philadelphia, Washington Reagan, Pittsburgh, Columbus, Chicago O'Hare) from NOAA GHCN-Daily, kept as `data/weather_daily.csv`. The analysis uses EIA's adjusted demand, sets to missing any hour more than 15% from the median of the five hours around it, and starts on 1 January 2016. The daily peak is the largest of at least 20 valid hours. `pjm.py` holds these rules, so the notebook and the model code share them.
- Why. EIA's adjusted series removes the 2,147,480,000 MW placeholder in the raw column but keeps single-hour spikes up to 224 GW, against a PJM record near 165 GW. The 15% rule flags 9 demand hours and 1 forecast hour, each an isolated spike, and no ordinary hour. In July 2015 PJM's forecast is about a third of demand in every hour, so the forecast baseline is unusable before August 2015; starting in 2016 also gives whole years. After cleaning there are 3,957 days, every one with a peak, and PJM's forecast of the peak is missing on 15. Its mean absolute error is 1.9%.
- Alternative. Population-weighted temperature over many stations, which tracks load better but needs a weighting we would have to justify. EIA's API instead of the bulk files, which needs a key. Dropping whole days with a spike instead of the spiked hour.
- Revisit. If temperature at five airports leaves a pattern in the residuals by region or season, add stations or weight them by load. These are observed temperatures; a purchase made the morning before only has a temperature forecast, and the model entry has to say how that gap is handled.

## 2026-11-13: Assumed costs for the loss until PJM's prices arrive

- Decision. Until we have a PJM Data Miner 2 API key, the loss uses stated costs per MWh of the peak hour instead of hourly prices. The base price is $50.70/MWh, PJM's 2025 load-weighted average day-ahead LMP. A shortfall costs c_u = $50/MWh more than buying it day-ahead, assuming the real-time price on a short day is about twice the day-ahead price. A surplus costs c_o = $10/MWh, assuming it resells in real time at about 20% below what it cost. The purchase is the α = c_u/(c_u + c_o) = 0.83 quantile of tomorrow's peak. Every score is also reported for c_u/c_o from 1 to 10, which is α from 0.50 to 0.91. All held-out scores before the price entry that replaces this one are provisional.
- Why. The proposal's loss needs day-ahead and real-time prices. We registered a PJM account on 13 November 2026 and asked for API access, which PJM grants to non-members by request; it will not arrive before the 18 November checkpoint. PJM's Independent Market Monitor reports 2025 load-weighted average LMPs of $50.70/MWh day-ahead and $50.73/MWh real-time, so the averages carry no premium. The cost of a miss comes from the real-time price moving with the error: real-time prices spike on days when load comes in above forecast. The $50 and $10 are assumptions about that asymmetry, not estimates, which is why the range is reported.
- Alternative. A symmetric loss (c_u = c_o), which makes the purchase the median and ignores that shortfalls cost more. Waiting for the key, which would miss the checkpoint. Daily day-ahead hub prices from EIA's wholesale market data, which have no real-time price and so give no c_u.
- Revisit. When the API key arrives, fetch hourly day-ahead and real-time LMPs for PJM-RTO, estimate c_u and c_o from the price on days we were short and long, and replace these values in a new entry. The prices stay off the public release because PJM's terms forbid redistribution; data/README.md will give the download command.

## 2026-11-13: Split by date, with 2025 onward held out

- Decision. Training days are 3 January 2016 to 31 December 2023 (2,898 days). The validation year is 2024 (362 days), used only to choose between methods. The held-out days are 1 January 2025 to 31 October 2026 (665 days); the cutoff date is 1 January 2025. After choosing on 2024, the model is refit on 2016 to 2024 and scored once on the held-out days. No seed is needed: the split is by date and the fit is a linear program with no random draw.
- Why. The decision is about tomorrow, so the test has to be later than the fit. Nearly two years held out covers two summers and two winters, which is where the expensive misses are, and includes the record 2025 and 2026 summer peaks. The first two days of 2016 drop because the model uses the peak two days before.
- Alternative. A random fraction of days, which would let the model see the days around each test day. A single held-out year, which has only one summer.
- Revisit. If we tune anything else on the held-out days by mistake, the score is no longer held-out and the entry that follows must say so.

## 2026-11-13: Score every rule in dollars on the peak hour

- Decision. A rule buys B MW for tomorrow's peak hour. Its loss on day D is c_u (Q_D − B)⁺ + c_o (B − Q_D)⁺ dollars, with the costs of the 2026-11-13 entry, and the score is the mean over the held-out days. We also report the share of days the buyer came up short. The baselines are buying PJM's day-ahead forecast of the peak, and buying the peak two days before, the last full day a buyer knows on the morning before.
- Why. The proposal's decision is the purchase, and its costs are lopsided, so RMSE would rank a rule that is often slightly short as good. The expected value of this loss is minimized by the c_u/(c_u + c_o) quantile of tomorrow's peak.
- Alternative. Scoring all 24 hours. The proposal's decision is the peak hour, and the instructor's comment on issue #3 notes that the maximum of 24 forecasts is not the forecast of the maximum.
- Revisit. The 2026-11-13 entry: real prices will replace c_u and c_o, and every dollar figure changes.

## 2026-11-13: Quantile regression on PJM's forecast as the first model

- Decision. A linear quantile regression of tomorrow's peak at τ = c_u/(c_u + c_o) = 0.833, on PJM's forecast of the peak, its excess above 110 GW, a weekend indicator, and PJM's miss two days before. It is fit by minimizing the pinball loss, solved exactly as a linear program with SciPy. The rule buys the fitted quantile. An 80% interval comes from refitting at τ = 0.1 and 0.9.
- Why. On the held-out days it loses $36,944 a day, against $72,360 for buying PJM's forecast and $268,153 for buying the peak two days before. Buying PJM's forecast scaled by its 0.83 quantile margin, 1.025, loses $37,713, so most of the gain comes from buying a quantile instead of the point forecast, which is the proposal's hypothesis. The 80% interval holds on 79.5% of held-out days. The model uses no observed temperature, because a buyer the morning before has only a forecast of it, and we have no archived temperature forecasts.
- Alternative. The 24-hour forecast-then-maximum approach, which issue #3 rules out. A model on temperature alone, which would need tomorrow's observed temperature and so would not be available when the purchase is made.
- Revisit. The generalized Pareto tail with temperature as a covariate, which issue #3 asks for, is the next model, scored against this one at the same quantile. We also have to confirm when PJM issues the forecast EIA-930 reports; if it is issued after the day-ahead market closes, the model is using information a buyer would not have.
