# Simulacija Web Servera

> Empirijska, diskretna simulacija redova cekanja HTTP zahtjeva
> koristeci 1.5 miliona stvarnih NASA logova iz 1995. godine.

> **Bosanski** | [English](README.en.md)

---

## Opis

Projekat analizira ponasanje web servera pod opterecenjem koristeci
**trace-driven simulaciju** -- umjesto teorijskog M/M/1 modela,
simulacija reprodukuje stvarne obrasce saobracaja iz NASA HTTP
logova.

Podaci sadrze 1,568,252 HTTP zahtjeva prikupljenih na serveru
NASA Kennedy Space Center-a tokom augusta 1995. Logovi se
automatski preuzimaju sa Kaggle-a putem `kagglehub` biblioteke.

### Zasto empirijska simulacija?

Teorijski modeli poput M/M/1 zahtijevaju da pristizanje zahtjeva
prati **Poissonov proces** i da velicina zahtjeva prati odredenu
**distribuciju**. Testiranjem na stvarnim podacima:

1. **Pristizanje nije Poissonovo** -- KS test odbacuje hipotezu
   (p < 0.05). Koristi se empirijsko presampliranje.
2. **Velicina zahtjeva ne prati lognormal ni Pareto** -- obje
   distribucije padaju na KS testu. Cuvamo cijeli trace.
3. **Presampliranje** -- simulacija nasumicno bira iz stvarnih
   izmjerenih vrijednosti, cuvajuci burstiness i varijabilnost
   realnog saobracaja.

---

## Cilj

Identificirati **tacku preopterecenja** (overload knee) web servera
-- nivo iskoristenja (ρ) nakon kojeg vrijeme cekanja
eksplozivno raste. Koristi se **Kneedle algoritam** za detekciju
koljena na krivulji odgovora.

---

## Rezultati

> **Napomena:** Ovi grafikoni se generisu automatski pokretanjem
> `python main.py all_sweep` (ili `docker compose run sim all_sweep`).

### Response time vs load
*P50, P95, P99 vrijeme cekanja u redu kroz 15 nivoa iskoristenja
(30 replikacija po nivou). Isprekidana vertikalna linija oznacava
saturaciju (ρ = 1.0).*

### Service time fit
*Distribucija velicine odgovora (bytes) sa lognormal i Pareto
prilagodjenim krivuljama.*

### Tabela ranih znakova preopterecenja

| ρ | ρ actual | p95 | × baseline | p99 | × baseline |
|---|---|---|---|---|---|
| 0.70 | 0.721 | 3.43s | 4.6× | 5.59s | 3.0× |
| 0.78 | 0.797 | 4.96s | 6.6× | 8.01s | 4.4× |
| **0.85** | **0.874** | **8.93s** | **11.9×** | **14.71s** | **8.0×** |
| 0.93 | 0.952 | 41.11s | 54.8× | 62.79s | 34.2× |
| 1.00 | 0.981 | 499.29s | 666.1× | 584.99s | 318.9× |

---

## Zakljucak

- **Kritična granica**: ρ ≈ 0.85 (λ ≈ 22.5 req/s) -- iznad ove
  tacke kasnjenje repa postaje neprihvatljivo (p95 > 8s).
- **Saturacija**: ρ ≈ 1.0 (λ ≈ 26.5 req/s) -- server je potpuno
  zasícen, vrijeme cekanja raste na stotine sekundi.
- **Kneedle knee**: ρ = 0.997 -- algoritam potvrdjuje saturaciju
  kao tacku maksimalne zakrivljenosti.
- **Nelinearna degradacija**: kasnjenje ne raste linearno --
  iznad ρ = 0.85 svako dodatno opterecenje izaziva eksponencijalan
  rast vremena cekanja.

---

## Arhitektura

```mermaid
flowchart LR
    A[NASA HTTP logovi] --> B[1. Ingestija]
    B --> C[2. Analiza]
    C --> D[3. Simulacija]
    D --> E[4. Load sweep]
    E --> F[5. Izvjestaj + plot]
    F --> G[Kneedle detekcija]
```

Detaljan opis svake faze: [dokumentacija arhitekture]
(docs/ARHITEKTURA.md).

---

## Pokretanje

### Bez Dockera (UV)

```bash
uv sync
python main.py all_sweep
```

### Sa Dockerom

```bash
docker compose build
docker compose run sim all_sweep
```

### Podkomande

| Komanda | Opis |
|---|---|
| `python main.py ingest` | Parsira raw NASA logove u parquet |
| `python main.py analyze` | Analizira sabbraćaj (Poisson test, distribucije) |
| `python main.py simulate` | Pokreće jednu simulaciju |
| `python main.py sweep` | Pokreće load sweep (15 nivoa × 30 replikacija) |
| `python main.py all` | Ingestija + analiza + simulacija |
| `python main.py all_sweep` | Ingestija + analiza + sweep |

---

## Reproducibilnost

- **Izvorni podaci**: NASA HTTP logovi (Kaggle dataset,
  `adchatakora/nasa-http-access-logs`), automatski preuzeti
- **Sjeme (seed)**: 42 (konfigurabilno)
- **Replikacije**: 30 po nivou opterecenja
- **Warmup period**: 500s (iskljucuje startup tranzijente)
- **Sve zavisnosti**: navedene u `pyproject.toml`

---

## Struktura projekta

```
├── main.py                 # Ulazna tacka (CLI dispatcher)
├── pyproject.toml          # Zavisnosti i konfiguracija alata
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Docker Compose konfiguracija
├── README.md               # Ova datoteka (Bosanski)
├── README.en.md            # English version
├── src/
│   ├── cli/                # CLI sloj (argparse, komande)
│   ├── ingestion/          # Parsiranje logova u parquet
│   ├── analysis/           # Karakterizacija saobracaja
│   ├── simulation/         # SimPy engine
│   └── experiment/         # Load sweep orchestrator
├── docs/
│   ├── ARHITEKTURA.md      # Arhitektura (Bosanski)
│   ├── ARCHITECTURE.md     # Architecture (English)
│   ├── IZVJESTAJ.md        # Izvjestaj (Bosanski)
│   └── REPORT.md           # Report (English)
└── data/                   # Generisani podaci (parquet, SVG, JSON, npy)
```

---

## Reference

- [Dokumentacija arhitekture (BS)](docs/ARHITEKTURA.md)
- [Architecture documentation (EN)](docs/ARCHITECTURE.md)
- [Izvjestaj o preopterecenju (BS)](docs/IZVJESTAJ.md)
- [Overload analysis report (EN)](docs/REPORT.md)
