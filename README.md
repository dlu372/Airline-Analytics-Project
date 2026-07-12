<div align="center">

# Airline Network Structure & Connectivity Analytics

**An interactive case study of network breadth, geographic reach, hub dependence, and codeshare-associated reach in the OpenFlights 2014 historical route-presence snapshot.**

**Di Lu**<br>
Information Systems & Business Analytics · University of Auckland

[**Live interactive dashboard**](https://dlu372.github.io/Airline-Analytics-Project/) · [Methodology](docs/methodology.md) · [Data quality](docs/data_quality.md)

</div>

<a href="https://dlu372.github.io/Airline-Analytics-Project/">
  <img src="docs/assets/dashboard-preview.png" alt="Preview of the Airline Network Structure and Connectivity Analytics dashboard, showing the 2014 historical snapshot, executive metrics, and network reach analysis." />
</a>

## Why this matters

Airline networks can be large without being geographically broad, and two similarly sized networks can depend on their origin airports in very different ways. Separating these structural dimensions supports better peer selection, network screening, hub-dependence assessment, airport-connectivity benchmarking, and questions about how codeshare listings alter apparent reach.

Air connectivity is also an enabling layer for access to people, markets, tourism, education, and regional participation. Network structure can help frame questions about accessibility, resilience, and dependency. This project does **not** measure social outcomes, economic impact, actual service frequency, or causality; it describes a historical network structure that can guide deeper investigation.

## At a glance

| Scope | Verified result |
|---|---:|
| Primary non-codeshare directed route presences | **52,296** |
| Airlines in the default comparison set (at least 50 presences) | **209** |
| Resolved airports in geographic analysis | **2,979** |
| Primary route presences eligible for geographic metrics | **99.7%** |
| Airline keys in the complete airline dimension | **566** |

The unit of analysis is one **directed airline–origin–destination route presence**. A presence is not a count of flights, departures, passengers, seats, demand, revenue, or current airline activity.

## Three flagship findings

### 1. Network breadth is not geographic reach

| Airline | Directed route presences | Countries reached |
|---|---:|---:|
| Ryanair (FR) | 2,484 | 29 |
| Turkish Airlines (TK) | 534 | 104 |
| Air France (AF) | 450 | 91 |

More route records do not automatically imply wider country coverage. Route breadth and geographic reach rank these historical networks differently, making both dimensions useful for airline peer comparison and network-positioning screening. Country coverage is taken from the endpoint-resolved `airline_geographic_reach` output—not from legacy geographic fields—and does not describe flight volume or commercial performance.

### 2. The same network size can have a very different hub structure

| Airline | Directed route presences | Effective hubs |
|---|---:|---:|
| UTair-Express | 74 | 19.28 |
| Tiger Airways | 74 | 3.89 |

At the same network size, UTair-Express distributes route presences much more evenly across origins than Tiger Airways. Higher effective-hub values indicate that route presences are distributed more evenly across origin airports. Route count therefore does not mechanically determine hub dependence. The comparison can screen for origin concentration and structural dependency, but it is not a measure of schedule intensity, passenger concentration, or operational performance.

### 3. Codeshare-associated reach is material for a subset

- **146** airlines have positive route-presence uplift when listed codeshare records are included; **420** have zero uplift.
- The top five airlines account for **30.88%** of total route-presence uplift.
- United Airlines (UA): **+1,273** route presences, **+247** airports, **+36** countries.
- KLM Royal Dutch Airlines (KL): **+620** route presences, **+260** airports, **+33** countries.

The uplift is the difference between the all-listed sensitivity view and the primary non-codeshare view. It identifies networks for partnership or coverage follow-up; it does not represent additional actual flights, capacity, revenue, or commercial benefit, and the codeshare flag does not identify the operating carrier.

## What this analysis supports

- Comparing airline network breadth with endpoint-resolved geographic reach
- Screening hub dependence and origin concentration among size-relevant peers
- Benchmarking historical airport connectivity and listed-carrier choice
- Testing sensitivity to codeshare-listed routes
- Identifying questions for deeper operational or commercial investigation

### What it does not support

- Flight-frequency, schedule, departure, or capacity analysis
- Passenger demand, traffic, or accessibility-outcome measurement
- Market-share estimation or monopoly claims
- Revenue, cost, or profitability analysis
- Present-day airline or network-strategy assessment
- Causal claims about economic or social outcomes

## Analytical approach

```mermaid
flowchart LR
  A[OpenFlights raw data] --> B[Checksum and schema validation]
  B --> C[Cleaning and enrichment]
  C --> D[Airport endpoint resolution]
  D --> E[Route-presence metrics]
  E --> F[Quality validation]
  F --> G[Analytics outputs]
  G --> H[Observable interactive dashboard]
```

The pipeline exposes a stable `airline_key`, builds a complete 566-row `dim_airline`, and resolves airport identity using unique airport codes while retaining explicit quality statuses. Geographic measures use only eligible resolved endpoints. Non-codeshare route presences form the primary structural comparison; codeshare-listed records form a sensitivity view. The dashboard defaults to airlines with at least 50 primary route presences, while the model retains the full airline population. Repeated clean rebuilds produced deterministic output hashes.

Detailed definitions are in the [methodology](docs/methodology.md), [terminology and claim boundaries](docs/terminology.md), [data-quality controls](docs/data_quality.md), and [validation report](docs/insight_validation.md).

## Technical implementation

| Layer | Implementation value |
|---|---|
| Python, pandas, NumPy | Modular loading, type control, endpoint resolution, metric construction, and repeatable output generation |
| SQLite | Portable analytical store with indexed fact tables and integrity checking |
| Observable Framework, JavaScript, HTML/CSS | Static interactive application with data-driven assertions, responsive charts, tooltips, and airline selection |
| Tests and validation | Metric regression tests, key checks, independent recalculation, deterministic-output verification, and responsive Playwright checks |
| Git, GitHub Actions, GitHub Pages | Reviewable checkpoints and reproducible static-site deployment without a backend or committed build artifacts |

## Data quality and methodological safeguards

- SHA-256 validation protects the three raw source files.
- Explicit schemas and nullable types prevent accidental join coercion.
- Airport and airline dimension keys are checked for duplicates.
- Airline-level metrics were independently recalculated from route presences.
- Endpoint identity resolution preserves conflict flags instead of silently replacing values.
- **52,163** primary route presences are retained for geographic metrics; **133** are explicitly excluded.
- The airport ID 5613 regression test confirms **0** geography-eligible rows, removing the known 16,000 km anomaly.
- Clean rebuild output hashes were identical; SQLite passes `PRAGMA integrity_check`.
- The current suite contains **10 passing tests** covering metric definitions, output contracts, raw checksums, keys, coverage accounting, and the 5613 regression.

## Reproduce locally

Python 3.12 and Node.js 22 are suitable reference environments.

```bash
pip install -r requirements.txt
python -m src.pipeline --clean
python -m unittest

npm ci
npm run dev -- --host 127.0.0.1 --port 3000
npm run build
```

The data pipeline writes reproducible processed and analytics outputs. The production Dashboard build is written to ignored `dist/`; the generated SQLite database, caches, and `node_modules/` are not committed.

## Repository structure

```text
src/                  Python analytics pipeline and metric definitions
analysis/             Read-only output validation utilities
tests/                Regression, contract, checksum, and integrity tests
dashboard/            Observable page, charts, styles, and build-time data loader
docs/                 Methodology, quality controls, validation, and preview asset
data/analytics/       Curated small outputs plus ignored generated detail/database
legacy/               Local audit archive of superseded analysis artifacts
.github/workflows/    GitHub Pages production deployment
```

## Current release and legacy Power BI

The interactive web dashboard is the current portfolio release. It is built on the revised route-presence semantics, stable identifiers, endpoint resolution, validated metrics, and explicit quality controls.

The [original PBIX](powerbi/airline_network_concentration.pbix) remains in the repository as a legacy artifact documenting an earlier project stage and Power BI experience. It does not represent the current methodology or accepted findings; the web release supersedes it without erasing the project’s development history.

## Data source, attribution, and licensing

The raw snapshot uses the OpenFlights airport, airline, and route datasets. OpenFlights states that route updates ceased in June 2014, so this project treats the data as historical only. Exact local source files are identified by `data/raw/checksums.sha256`.

Original code in this repository is licensed under the [MIT License](LICENSE). This does not relicense third-party data.

OpenFlights’ [data page](https://openflights.org/data.php) states that its Airport, Airline, Plane, and Route databases are available under the Open Data Commons Open Database License 1.0 (ODbL 1.0), with individual database contents under the Database Contents License 1.0 (DbCL 1.0). The OpenFlights raw data and applicable derived database content retain those terms. See [DATA_LICENSE.md](DATA_LICENSE.md) for the scope boundary, attribution, and links to the source license texts.

## Author

**Di Lu**<br>
Information Systems & Business Analytics<br>
University of Auckland<br>
[GitHub](https://github.com/dlu372)
