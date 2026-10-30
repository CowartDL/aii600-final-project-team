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
