# Ingestion phase

Outputs a `data/parsed.parquet` file containing 1,568,252 records e.g.:

```
host:      in24.inetnebr.com
timestamp: 1995-08-01 00:00:01-04:00
method:    GET
path:      /shuttle/missions/sts-68/news/sts-68-mcc-05.txt
status:    2000
bytes:     1839.0
```

# Analysis phase

Runs via the `TrafficCharacterizer` class.

1. **Load parquet** — load the dataframe from `data/parsed.parquet`.

2. **Rate binning** — bin arrivals into 60 s intervals.
   - Outputs rate min, rate max, and rate mean.
   - Plots the rate series to `rate_series.svg` (shows bursts).
   - Writes statistics to `characterization.json` (used for the load
     sweep in later phases).

3. **Test arrivals as a Poisson process** — parametric bootstrap GoF KS
   test (Monte Carlo + KS, better than plain KS).
   - Writes arrival verdict to `characterization.json`.
   - Plots inter-arrival histogram and Q-Q plot against exponential.
   - Decides whether the server can be modelled as an M/M/C queue.
   - **Result:** no — fallback to empirical simulation.

4. **Service time handling** — logs provide byte sizes, not service
   times (larger files take longer to transmit).
   - Extracts the `bytes` column, drops missing and zero-size
     responses.
   - Fits lognormal and Pareto via MLE (both heavy-tailed, matching
     real server load).
   - **Pareto wins** by AIC, but even Pareto fails the parametric
     bootstrap KS test (p < 0.05).
   - **Result:** neither distribution fits well — save the full
     byte-size trace to `data/empirical_service_sizes.npy` for
     empirical resampling in the simulation.
   - Plots the byte-size histogram with lognormal and Pareto overlays
     for visual confirmation (`service_time_fit.svg`).
