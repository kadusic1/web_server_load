> **Bosanski** | [English](ARCHITECTURE.md)

# Faza ingestije

Output je `data/parsed.parquet` fajl koji sadrzi 1,568,252 zapisa:

```
host:      in24.inetnebr.com
timestamp: 1995-08-01 00:00:01-04:00
method:    GET
path:      /shuttle/missions/sts-68/news/sts-68-mcc-05.txt
status:    2000
bytes:     1839.0
```

# Faza analize

Pokrece se kroz `TrafficCharacterizer` klasu.

1. **Ucitaj parquet** — ucitava dataframe iz `data/parsed.parquet`.

2. **Grupisanje po stopi (rate binning)** — grupise dolaske u
   intervale od 60 s.
   - Izracunava min, max i srednju stopu dolazaka.
   - Crta seriju stopa u `rate_series.svg` (prikazuje burstove).
   - Upisuje statistiku u `characterization.json` (koristi se za
     load sweep u kasnijim fazama).

3. **Testiraj dolaske kao Poissonov proces** — parametric bootstrap
   GoF KS test (Monte Carlo + KS, bolji od obicnog KS).
   - Upisuje verdict u `characterization.json`.
   - Crta histogram medjudolaznih vremena i Q-Q plot u odnosu na
     eksponencijalnu distribuciju.
   - Odlucuje da li server moze biti modeliran kao M/M/C red.
   - **Rezultat:** ne — koristi se empirijska simulacija.

4. **Obrada vremena usluge (service time)** — logovi daju velicinu
   u bajtovima, a ne vrijeme usluge (veci fajlovi duze traju).
   - Ekstrahuje kolonu `bytes`, uklanja nedostajuce i nulte
     vrijednosti.
   - Prilagodjava lognormal i Pareto putem MLE (oba su
     heavy-tailed, sto odgovara stvarnom serveru).
   - **Pareto pobijedjuje** po AIC-u, ali cak ni Pareto ne
     prolazi parametric bootstrap KS test (p < 0.05).
   - **Rezultat:** nijedna distribucija ne odgovara dobro — cijeli
     trace velicina se cuva u `data/empirical_service_sizes.npy`
     za empirijsko presampliranje u simulaciji.
   - Crta histogram velicina sa lognormal i Pareto krivuljama za
     vizuelnu potvrdu (`service_time_fit.svg`).

# Faza simulacije

Pokrece se kroz `SimulationEngine` klasu.

1. **Ucitaj konfiguraciju** — instancira `SimulationConfig` sa
   podrazumijevanim vrijednostima: `servers=1`, `sim_time=10_000s`,
   `warmup=500s`, `seed=42`, `monitor_interval=0.1s`,
   `bandwidth=500_000 B/s`, i putanjama do
   `data/empirical_interarrivals.npy` i
   `data/empirical_service_sizes.npy`.

2. **Ucitaj empirijske trace-ove** — `np.load()` dva `.npy` fajla
   proizvedena u fazi analize.
   - Konvertuje velicine bajtova u vremena usluge:
     `sizes / bandwidth`.
   - Kreira `EmpiricalArrival(interarrivals)` i
     `EmpiricalService(service_times)`. Oba presampliraju svoj
     trace putem `rng.choice()` pri svakom pozivu.

3. **Instanciraj engine** — `SimulationEngine(arrival, service, cfg)`.

4. **Pokreni engine** — `engine.run()` orkestrira SimPy simulaciju:
   - Kreira `simpy.Environment()` i `simpy.Resource` pool sa
     `capacity=servers`.
   - Kreira `_StatsCollector(warmup)` — odbacuje sve uzorke prije
     warmup cut-off-a da bi se iskljucili startup tranzijenti.
   - Pokrece nezavisne RNG tokove putem
     `np.random.default_rng(seed).spawn(2)` — jedan za dolaske,
     jedan za usluge — osiguravajuci deterministicku
     reprodukcibilnost.
   - Registruje tri konkurentna SimPy procesa:
     * **`_arrival_process`** — beskonacna petlja: uzima
       `next_interarrival()`, ceka `env.timeout(gap)`, zatim
       pokrece `_request_lifecycle` za zahtjev.
     * **`_request_lifecycle`** (jedan po zahtjevu) — dobija slot
       na serveru putem `resource.request()`, biljezi vrijeme
       cekanja, ceka `env.timeout(service_time)`, biljezi odlazak.
     * **`_monitor_process`** — svakih `monitor_interval` sekundi
       uzorkuje duzinu reda i broj zauzetih servera.
   - Izvrsava sa `env.run(until=sim_time)`.

5. **Agregiraj rezultate** — `collector.result(lambda_, mu, cfg)`
   izracunava:
   - `avg_wait` — srednje vrijeme cekanja u redu (zahtjevi koji
     stizu nakon warmup-a).
   - `avg_queue_length` — vremenski ponderisana sredina uzoraka
     duzine reda.
   - `server_utilization` — `avg_busy / servers` (ograniceno na 1.0).
   - `total_requests` — odlasci nakon warmup-a.

   Vraca `SimulationResult` dataclass.

6. **Izlaz** — rezultat se loguje putem `loguru`.

# Faza orkestracije eksperimenta

Pokrece se kroz `ExperimentOrchestrator` klasu.

1. **Ucitaj konfiguraciju** — instancira `ExperimentConfig`, koji
   sadrzi `SimulationConfig` za parametre po pokretanju.

2. **Ucitaj empirijske trace-ove** — `np.load()` medjudolazna
   vremena i velicine usluga iz faze analize.
   - Izracunava `mu = bandwidth / mean(service_sizes)` — stopa
     usluge (zahtjevi/s).
   - Izracunava `lambda_0 = 1 / mean(interarrivals)` — osnovna
     stopa dolazaka.

3. **Generisi rho tacke** — 15 nejednoliko rasporedjenih nivoa
   iskoristenja od 0.1 do 1.5, koncentrisanih oko zone koljena
   0.7–1.3.

4. **Za svaki nivo rho** (sekvencijalno, jedan po jedan):
   - Skalira medjudolazni trace:
     `interarrivals * lambda_0 / (rho * servers * mu)` da bi
     se promijenila stopa dolazaka uz ocuvanje burstiness-a.
   - **Pokrece 30 replikacija** sekvencijalno, svaka sa
     inkrementiranim seed-om (`sim_config.seed + i`) za
     deterministicku varijabilnost. Svaka replikacija kreira
     svoj `SimulationEngine`.
   - **Agregira rezultate:**
     * Srednje vrijeme cekanja kroz replikacije.
     * 95% t-interval povjerenja (df = 29) za srednju vrijednost.
     * p50 / p95 / p99 iz objedinjenih vremena cekanja.
     * Izmjereni rho (srednje iskoristenje servera kroz
       replikacije).
   - Odbacuje raw vremena cekanja nakon agregacije — samo se
     sazeti red zadrzava.

5. **Izlaz** — upisuje `data/experiment_results.json` sa
   konfiguracijom i jednim `LoadLevelRow` po nivou rho. Svaki red
   sadrzi: `rho`, `rho_actual`, `mean_wait`, `ci_lower`,
   `ci_upper`, `p50_wait`, `p95_wait`, `p99_wait`,
   `n_replications`.

   Orkestrator zatim automatski generise plot vremena odgovora u
   odnosu na opterecenje (vidi fazu izvjestaja).

# Faza izvjestaja

Pokrece se automatski kao zavrsni korak
`ExperimentOrchestrator.run()`, odmah nakon upisivanja
`experiment_results.json`.

1. **Ucitaj agregirane rezultate** — cita `ExperimentResult`
   dataclass proizveden od strane load sweep-a (u memoriji, bez
   ponovnog citanja JSON-a).

2. **Nacrtaj response-time-vs-load** —
   `plot_response_time_vs_load(result)`:
   - x-osa: izmjereno iskoristenje `rho_actual`
   - y-osa: vrijeme cekanja u redu (sekunde), **log skala**
   - Tri linije percentila: p50 (plava `#0173B2`), p95 (narandzasta
     `#DE8F05`), p99 (ljubicasta `#CC78BC`)
   - 95% CI traka oko srednje vrijednosti (poluprozirna plava)
   - Isprekidana vertikalna linija na `rho = 1.0` (saturacija)

3. **Izlaz** — upisuje `data/response_time_vs_load.svg`.

4. **Detekcija koljena preopterecenja** —
   `compute_overload_analysis(result, mu)`:
   - Pokrece **Kneedle algoritam** (Satopaa et al. 2011) na
     izmjerenom iskoristenju (`rho_actual`) u odnosu na p99
     vrijeme cekanja sa `curve='convex', direction='increasing',
     S=1.0`.
   - Izracunava osnovnu liniju niskog opterecenja (srednja
     vrijednost p95 / p99 iz prva 3 nivoa rho).
   - Pronalazi rho koljena, lambda koljena i faktore po nivou.

5. **Izlaz** — upisuje `data/overload_analysis.json` sa svim
   izracunatim vrijednostima (mu, baseline, knee fields, per-level
   factor array).

Plot, analiza i log trajanja sweep-a se generisu automatski nakon
svakog `python main.py sweep`.

Sve numericke vrijednosti su unaprijed izracunate u
`data/overload_analysis.json`; markdown se pise rucno, ne
generise ga kod.
