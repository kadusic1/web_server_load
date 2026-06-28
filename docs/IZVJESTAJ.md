> **Bosanski** | [English](REPORT.md)

# Load-Sweep Eksperiment: Analiza Preopterecenja

**Izvorni podaci:** `data/experiment_results.json` (15 nivoa rho,
30 replikacija po nivou)
**Izracunate vrijednosti:** `data/overload_analysis.json`

> [!NOTE]
> Ovi fajlovi se generisu od strane `load-sweep` eksperimenta.
> Pokrenite `python main.py all_sweep` da biste ih proizveli.

## Metoda

Koljeno preopterecenja detektovano je pomocu **Kneedle algoritma**
na izmjerenom iskoristenju (`rho_actual`) u odnosu na p99 vrijeme
cekanja, sa `curve='convex', direction='increasing', S=1.0`.
Osnovna linija niskog opterecenja je srednja vrijednost p95 / p99
iz prva 3 nivoa rho.

## Rezultat

- **Osnovna linija (nisko opterecenje):** p95 = 0.75s, p99 = 1.83s
- **Kneedle koljeno:** rho = 0.997 (rho_actual), lambda = 26.4 req/s
- **Na koljenu:** p50 = 1905s, p95 = 3469s, p99 = 3626s

Rani znaci preopterecenja pojavljuju se znatno prije koljena:

| rho | rho_actual | p95 | × osnovna linija | p99 | × osnovna linija |
|---|---|---|---|---|---|
| 0.70 | 0.721 | 3.43s | 4.6× | 5.59s | 3.0× |
| 0.78 | 0.797 | 4.96s | 6.6× | 8.01s | 4.4× |
| **0.85** | **0.874** | **8.93s** | **11.9×** | **14.71s** | **8.0×** |
| 0.93 | 0.952 | 41.11s | 54.8× | 62.79s | 34.2× |
| 1.00 | 0.981 | 499.29s | 666.1× | 584.99s | 318.9× |

## Zakljucak

Server ulazi u preopterecenje iznad rho = 0.85 (lambda = 22.5 req/s)
i potpuno je zasícen na rho = 1.0 (lambda = 26.5 req/s). Kasnjenje
repa (tail latency) degradira nelinearno iznad rho = 0.85 i postaje
neprihvatljivo (p95 > 8s) ubrzo nakon toga. Kneedle koljeno na
rho = 0.997 potvrdjuje saturaciju kao tacku maksimalne
zakrivljenosti.
