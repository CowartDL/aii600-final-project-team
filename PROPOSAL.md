# Proposal

## Hypothesis

Buying tomorrow's peak-hour energy at a quantile of a calibrated forecast distribution, instead of at a specific point forecast, lowers the expected cost of serving PJM load. PJM is a major Regional Transmission Organization for the Mid-Atlantic region. The quantity is PJM's peak hourly demand on the next day, in MW, forecast on the morning of the day before, for each day of a projected later period.

## Data

The source we are using is from the U.S. Energy Information Administration's Hourly Electric Grid Monitor (form EIA-930). The unit of observation is one hour of PJM demand in megawatts (MW), and the series starts in July 2015. Through October 2026 that is about 99,000 hourly rows, or about 4,100 daily peaks. PJM reports the values to EIA, and the same series includes PJM's own day-ahead demand forecast, which is one of our baselines. Daily temperatures for a few PJM cities come from NOAA's Global Historical Climatology Network. Both are U.S. government data in the public domain, so the files can go on the `data` release. Day-ahead and real-time prices from PJM Data Miner set the costs in the loss. If PJM's terms do not allow republishing those, they stay off the release and `data/README.md` will give the download command.

The measurement is not quite the quantity the decision needs. EIA-930 reports an hourly average, not the instantaneous peak. The values are preliminary and have gaps and spikes that we have to clean. Rooftop solar is not metered by the grid, so it lowers reported demand during the day, and its growth shifts the series over time. The reporting errors are noise. The solar trend is a bias that grows over the sample and creates some uncertainty in the results.

## Decision affected by the model

A load-serving utility in PJM buys energy for tomorrow's peak hour in the day-ahead market. It decides how many MW to buy, B, at the day-ahead price. If demand Q comes in higher, it buys the shortfall at the real-time price. If demand comes in lower, it sells the surplus back at the real-time price. With underage cost c_u (the real-time premium over day-ahead) and overage cost c_o (the loss on resale), the expected cost is c_u E[(Q − B)⁺] + c_o E[(B − Q)⁺]. The cost is minimized by buying the c_u/(c_u + c_o) quantile of tomorrow's forecast. Buying too little costs more, because real-time prices spike on the hottest and coldest days, which are the days a shortfall is most likely. To keep the problem to one buyer, we treat all of PJM's load as that utility's load. The costs per MW scale to a smaller utility.
