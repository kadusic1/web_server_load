# Load-Sweep Experiment: Overload Analysis

**Source data:** `data/experiment_results.json` (15 rho levels, 30
replications per level)
**Computed values:** `data/overload_analysis.json`

> NOTE: You need to run the sweep to have these files.

## Method

Overload knee detected via the **Kneedle algorithm** applied to measured utilisation (`rho_actual`) vs p99 wait time,
with `curve='convex', direction='increasing', S=1.0`. Low-load baseline
is the mean p95 / p99 from the first 3 rho levels.

## Result

- **Low-load baseline:** p95 = 0.75s, p99 = 1.83s
- **Kneedle knee:** rho = 0.997 (rho_actual), lambda = 26.4 req/s
- **At knee:** p50 = 1905s, p95 = 3469s, p99 = 3626s

Early overload signs appear well before the knee:

| rho | rho_actual | p95 | x baseline | p99 | x baseline |
|---|---|---|---|---|---|
| 0.70 | 0.721 | 3.43s | 4.6x | 5.59s | 3.0x |
| 0.78 | 0.797 | 4.96s | 6.6x | 8.01s | 4.4x |
| **0.85** | **0.874** | **8.93s** | **11.9x** | **14.71s** | **8.0x** |
| 0.93 | 0.952 | 41.11s | 54.8x | 62.79s | 34.2x |
| 1.00 | 0.981 | 499.29s | 666.1x | 584.99s | 318.9x |

## Conclusion

The server approaches overload above rho = 0.85 (lambda = 22.5 req/s)
and is fully saturated at rho = 1.0 (lambda = 26.5 req/s). Tail latency
degrades non-linearly beyond rho = 0.85 and becomes unacceptable
(p95 > 8s) shortly after. The Kneedle knee at rho = 0.997 confirms
saturation as the point of maximum curvature.
