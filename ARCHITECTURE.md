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

# Simulation phase

Runs via the `SimulationEngine` class.

1. **Load config** — instantiate `SimulationConfig` with defaults:
   `servers=1`, `sim_time=10_000s`, `warmup=500s`, `seed=42`,
   `monitor_interval=0.1s`, `bandwidth=500_000 B/s`, and paths to
   `data/empirical_interarrivals.npy` and
   `data/empirical_service_sizes.npy`.

2. **Load empirical traces** — `np.load()` the two `.npy` files produced
   by the analysis phase.
   - Converts byte sizes to service times: `sizes / bandwidth`.
   - Creates `EmpiricalArrival(interarrivals)` and
     `EmpiricalService(service_times)`. Both resample their trace via
     `rng.choice()` on each call.

3. **Instantiate engine** — `SimulationEngine(arrival, service, cfg)`.

4. **Run the engine** — `engine.run()` orchestrates a SimPy simulation:

   - Creates `simpy.Environment()` and a `simpy.Resource` pool with
     `capacity=servers`.
   - Creates `_StatsCollector(warmup)` — discards all samples before
     the warmup cutoff to exclude start-up transients.
   - Spawns independent RNG streams via
     `np.random.default_rng(seed).spawn(2)` — one for arrivals, one
     for services — ensuring deterministic reproducibility.
   - Registers three concurrent SimPy processes:
     * **`_arrival_process`** — infinite loop: draws
       `next_interarrival()`, yields `env.timeout(gap)`, then spawns
       a `_request_lifecycle` for the request.
     * **`_request_lifecycle`** (one per request) — acquires a server
       slot via `resource.request()`, records wait time, yields
       `env.timeout(service_time)`, records departure.
     * **`_monitor_process`** — every `monitor_interval` seconds,
       samples queue length and busy server count.
   - Executes with `env.run(until=sim_time)`.

5. **Aggregate results** — `collector.result(lambda_, mu, cfg)` computes:
   - `avg_wait` — mean queue wait time (requests arriving after warmup).
   - `avg_queue_length` — time-weighted mean of queue-length samples.
   - `server_utilization` — `avg_busy / servers` (capped at 1.0).
   - `total_requests` — departures after warmup.

   Returns a `SimulationResult` dataclass.

6. **Output** — the result is logged via `loguru`

# Experiment Orchestration phase

Runs via the `ExperimentOrchestrator` class.

1. **Load config** — instantiate `ExperimentConfig`, which nests a
   `SimulationConfig` for per-run parameters.

2. **Load empirical traces** — `np.load()` inter-arrival times and
   service byte sizes from the analysis phase.
   - Computes `mu = bandwidth / mean(service_sizes)` — service rate
     (requests/sec).
   - Computes `lambda_0 = 1 / mean(interarrivals)` — base arrival rate.

3. **Generate rho points** — 15 non-uniformly spaced utilisation
   points from 0.1 to 1.5, concentrated around the 0.7–1.3 knee zone.

 4. **For each rho level** (sequential, one at a time):
    - Scales inter-arrival trace:
      `interarrivals * lambda_0 / (rho * servers * mu)` to shift the
      arrival rate while preserving the trace's burstiness.
    - **Runs 30 replications** sequentially, each with an incremented
      seed (`sim_config.seed + i`) for deterministic variability.
      Each replication creates its own `SimulationEngine`.
   - **Aggregates results:**
     * Mean wait time across replications.
     * 95% t-confidence interval (df = 29) on the mean.
     * p50 / p95 / p99 from pooled per-request wait times.
     * Measured rho (mean server utilisation across replications).
   - Discards raw per-request waits after aggregation — only the
     summary row persists.

5. **Output** — writes `data/experiment_results.json` with config
   metadata and one `LoadLevelRow` per rho level. Each row contains:
   `rho`, `rho_actual`, `mean_wait`, `ci_lower`, `ci_upper`,
   `p50_wait`, `p95_wait`, `p99_wait`, `n_replications`.
