# Version-control and generated-file strategy

## Recommended classification

| Category | Examples | Git recommendation | Reason |
|---|---|---|---|
| Source code | `src/`, compatibility wrapper, `analysis/` | Track | Required to reproduce pipeline and audit |
| Documentation | `docs/`, README, SQL status notes | Track | Methodology and claim boundaries are core deliverables |
| Tests | `tests/` | Track | Protect metric definitions and reproducibility |
| Raw source data | three `.dat` files and checksum manifest | Track, with source/license attribution | Immutable snapshot is about 4 MB and exact version matters |
| Reproducible processed output | `data/processed/*.csv` | Generate; do not track long term | About 19 MB, high line churn, fully reproducible |
| Curated analytics showcase | small summary CSVs and quality JSON | Track selectively | Useful for GitHub review without running pipeline |
| Large analytics detail | `route_carrier_diversity.csv` | Generate; do not track | 4.3 MB and 33,854 rows; high churn |
| Generated database | 50 MB SQLite | Do not track | Reproducible binary causes repository bloat and opaque diffs |
| Legacy artifact | old SQL/CSV/DB/PBIX/PNG | Temporary archive only | Superseded or methodologically invalid |

## SQLite decision

`data/analytics/airline_network_analytics.sqlite` should not be committed. At
about 50 MB it is below GitHub's hard single-file limit but still creates major
history bloat, has no useful text diff, and is deterministically rebuilt in
about 27 seconds. Add it to `.gitignore` and make the pipeline/test suite the
source of truth.

The 13 MB legacy database and empty 8 KB database should not remain on the main
branch after explicit removal approval. Git history already preserves them.

## CSV decision

Recommended showcase files to track after endpoint-quality correction:

- `airline_network_summary.csv` — 45 KB;
- `airline_hub_dependence.csv` — 51 KB;
- `airline_geographic_reach.csv` — 64 KB;
- `airport_connectivity.csv` — 203 KB;
- `codeshare_sensitivity.csv` — 89 KB;
- `data_quality.json` — about 2 KB.

Together they are small enough for GitHub inspection. They should be generated
in CI and checked for a clean diff so that committed examples cannot drift from
the pipeline.

Do not track:

- `route_carrier_diversity.csv` unless a small curated sample is added for
  portfolio display;
- the four processed CSVs once CI/pipeline generation is established;
- temporary SQLite files or Python caches.

An all-generated/no-CSV policy would be technically cleaner, but selective
small analytics exports are useful for a portfolio repository. Do not mix
tracked and generated status without explicit `.gitignore` exceptions and a CI
freshness check.

## Proposed ignore policy for a later change

Do not apply this until the owner confirms the selective-export policy:

```gitignore
data/processed/*.csv
data/analytics/*.sqlite
data/analytics/route_carrier_diversity.csv
```

If all analytics CSVs are generated-only, use `data/analytics/*.csv` instead and
retain only `data_quality.json` or a small `examples/` export.

## Legacy PBIX, PNG, SQL, and database policy

- Current PBIX: move to `legacy/powerbi/` with a clear invalid-methodology note;
  remove it from the main branch after the replacement PBIX is accepted.
- Current PNGs: move to `legacy/report/`; delete from the active README because
  they visualize retired metrics.
- Legacy SQL: small enough to retain during review, but Git history is a better
  long-term archive; remove after the new methodology is stable.
- Legacy databases: remove after explicit approval; do not use Git LFS for
  reproducible superseded databases.
- New PBIX and selected screenshots: track only the accepted final version and
  clearly document its input tables and refresh procedure.

## Source and licensing note

Before publishing, add OpenFlights source date, download location, and database
license/attribution information. The raw checksum proves file identity but does
not replace attribution or licensing documentation.

## Commit boundaries for the current work

When approved, prefer separate commits:

1. Phase 1/2 source, docs, tests, checksum, and legacy moves;
2. generated-output tracking/ignore policy;
3. endpoint-resolution and airline-dimension corrections;
4. replacement dashboard artifacts.

This keeps generated binaries and methodology corrections reviewable.
