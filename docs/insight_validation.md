# Phase 2 analytics validation and candidate insights

## Scope and claim boundary

This audit validates the six Phase 2 output tables against the canonical SQLite
route-presence tables. The unit is a directed airline–origin–destination route
presence in the OpenFlights 2014 historical snapshot. Results do not measure
flight frequency, passengers, capacity, revenue, profitability, operational
performance, market share, or current airline strategy.

The primary network excludes codeshare rows and is only an operating-network
proxy. All-listed results are sensitivity views, not verified operating routes.

Reproduce the audit with:

```bash
python analysis/validate_outputs.py
```

## 1. Output consistency

| Table | Rows | Columns | Duplicate primary keys | Missing airline ID | Missing airline name |
|---|---:|---:|---:|---:|---:|
| airline_network_summary | 564 | 14 | 0 | 20 | 20 |
| airline_hub_dependence | 564 | 10 | 0 | 20 | 20 |
| airline_geographic_reach | 564 | 15 | 0 | 20 | 20 |
| airport_connectivity | 2,988 | 12 | 0 | n/a | n/a |
| route_carrier_diversity | 33,854 | 12 | 0 | n/a | n/a |
| codeshare_sensitivity | 566 | 23 | 0 | 20 | 20 |

The three 564-row airline tables contain exactly the same internal airline-key
set. `codeshare_sensitivity` contains all 564 plus two airlines that have only
codeshare-listed records after endpoint validation:

| Airline ID | Code | Name | Non-codeshare routes | All-listed routes |
|---:|---|---|---:|---:|
| 16120 | Z6 | ZABAIKAL AIRLINES | 0 | 20 |
| 16150 | YO | TransHolding System | 0 | 2 |

Power BI must not inner-join the sensitivity table to the 564-row tables. The
recommended model is a 566-row airline dimension with a stable `airline_key`,
one-to-many relationships to each fact table, and an explicit flag for whether
a non-codeshare network is available. The current CSV outputs do not expose the
internal fallback airline key, so this is a required pipeline change before the
model is rebuilt.

Other identifier findings:

- airport_connectivity has a unique, non-missing `airport_id` primary key;
- route_carrier_diversity has a unique `(source_airport_id,
  destination_airport_id)` key;
- no airline name maps to multiple airline keys in the 564-row summary;
- 20 airline rows use code-based fallback identity and have no airline ID/name;
- all 564 summary rows have an airline code;
- 519 airlines are marked active, 25 inactive, and 20 unknown;
- 197 directed-OD rows have a missing source or destination IATA display code.

Inactive airlines should remain because this is a historical snapshot and the
source `active` flag is not a reliable statement of current operations. It
should be a descriptive/filter field, not a default exclusion rule. Missing
IATA values must not remove records: airport ID is the analytical key, with IATA
used only for display.

## 2. Independent metric recalculation

Eleven systematically selected airlines were recalculated from
`route_presences_non_codeshare`: three largest networks, three 20–100-route
low-country-coverage examples, three high-HHI networks with at least 50 routes,
and three low-HHI networks with at least 50 routes. The maximum absolute
difference across route counts, airport counts, international share,
reciprocity, top-1/top-3 share, origin HHI, effective hubs, median distance, and
P90 distance was `5.1e-12`. This is floating-point noise only.

### Calculation trace from route presence to metric

For every sampled airline the audit independently performs these steps:

1. deduplicate `(airline_key, source_airport_id, destination_airport_id)`;
2. count rows for `directed_route_presences` and distinct endpoint IDs for
   origin/destination breadth;
3. compare known source/destination countries for international share;
4. test whether each `(O,D)` has `(D,O)` for reciprocal share;
5. count routes by origin, divide by airline total, and derive top-1, top-3,
   `sum(share^2)`, and its inverse;
6. calculate each valid route's haversine distance, then take median and P90;
7. group the primary network by directed OD and count distinct airline keys;
8. calculate codeshare uplift as all-listed minus non-codeshare.

Worked hub example: Tiger Airways has 74 primary route presences. SIN accounts
for 37, so top-1 is `37/74 = 0.5`. TPE and MNL contribute one each, so top-3 is
`39/74 = 0.527027`. Squaring and summing every origin share gives HHI
`0.256757`, and the inverse gives `3.894737` effective hubs. By contrast,
UTair-Express also has 74 routes, but its top three origins contribute 7, 6,
and 6 routes; its HHI is `0.051863` and effective hubs `19.281690`.

### Selected airline evidence

Largest route-presence networks:

| Code | Airline | Routes | Distinct airports | Countries |
|---|---|---:|---:|---:|
| FR | Ryanair | 2,484 | 176 | 29 |
| US | US Airways | 1,446 | 280 | 59 |
| AA | American Airlines | 1,265 | 259 | 64 |

Historical regional-airline examples were selected only where the source
airline name clearly identifies a regional carrier:

| Code | Airline | Routes | Airports | Countries |
|---|---|---:|---:|---:|
| ZL | Regional Express | 88 | 35 | 1 |
| 9K | Cape Air | 84 | 39 | 6 |
| 8E | Bering Air | 65 | 27 | 1 |

High hub dependence among airlines with at least 50 routes:

| Code | Airline | Routes | Top-1 origin share | Origin HHI |
|---|---|---:|---:|---:|
| NX | Air Macau | 52 | 0.5000 | 0.259615 |
| TR | Tiger Airways | 74 | 0.5000 | 0.256757 |
| LO | LOT Polish Airlines | 96 | 0.5000 | 0.255208 |

Low hub dependence under the same minimum:

| Code | Airline | Routes | Top-1 origin share | Origin HHI |
|---|---|---:|---:|---:|
| FR | Ryanair | 2,484 | 0.049919 | 0.013692 |
| CZ | China Southern Airlines | 1,232 | 0.090909 | 0.023933 |
| U2 | easyJet | 1,130 | 0.089381 | 0.024429 |

### Airport and directed-OD checks

| Airport | Outgoing destinations | Incoming origins | Outgoing listed airlines | Reciprocity |
|---|---:|---:|---:|---:|
| CDG | 237 | 233 | 104 | 0.970464 |
| FRA | 225 | 225 | 90 | 0.977778 |
| ISL | 224 | 227 | 60 | 0.973214 |

The maximum listed-carrier count is 10. The highest rows are TPE→NRT,
NRT→TPE, and HKG→ICN, each with 10 listed carriers. These are historical listed
carrier counts, not service frequency or market competition measures.

## 3. Distribution audit

### Airline network and hub metrics

| Metric | Min | Median | Mean | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| directed_route_presences | 1 | 31 | 92.72 | 90.25 | 225.4 | 369.4 | 2,484 |
| distinct_origin_airports | 1 | 14 | 28.00 | 35 | 69.7 | 96.55 | 268 |
| distinct_destination_airports | 1 | 14 | 28.03 | 35 | 69.4 | 95.85 | 275 |
| distinct_countries | 1 | 4 | 9.64 | 11 | 26 | 35.85 | 104 |
| international route-presence share | 0 | 0.500 | 0.498 | 0.919 | 1.000 | 1.000 | 1.000 |
| reciprocal route share | 0 | 1.000 | 0.942 | 1.000 | 1.000 | 1.000 | 1.000 |
| top1_origin_share | 0.0499 | 0.3333 | 0.3307 | 0.4444 | 0.5000 | 0.5000 | 1.0000 |
| top3_origin_share | 0.1107 | 0.5417 | 0.5731 | 0.6667 | 1.0000 | 1.0000 | 1.0000 |
| origin_airport_hhi | 0.01369 | 0.17032 | 0.19541 | 0.25000 | 0.36250 | 0.50000 | 1.00000 |
| effective_hubs | 1.00 | 5.87 | 8.11 | 9.84 | 15.51 | 20.75 | 73.04 |

### Geographic, connectivity, and carrier-choice metrics

| Metric | Min | Median | Mean | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| mean distance km | 19 | 1,104 | 1,377 | 1,924 | 2,853 | 3,611 | 7,266 |
| median distance km | 19 | 896 | 1,188 | 1,558 | 2,411 | 3,000 | 8,451 |
| P90 distance km | 19 | 1,809 | 2,560 | 3,379 | 6,658 | 8,000 | 16,010 |
| airport outgoing destinations | 0 | 3 | 11.33 | 8 | 31 | 55 | 237 |
| airport outgoing listed airlines | 0 | 2 | 5.28 | 5 | 13 | 23 | 104 |
| listed_carrier_count per OD | 1 | 1 | 1.545 | 2 | 3 | 3 | 10 |

### Codeshare sensitivity

| Metric | Min | Median | Mean | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| route_presence_uplift | 0 | 0 | 25.57 | 2 | 32 | 137.5 | 1,273 |
| airport_coverage_uplift | 0 | 0 | 5.70 | 0 | 8.5 | 29 | 260 |
| country_coverage_uplift | 0 | 0 | 1.19 | 0 | 2.5 | 6 | 49 |
| top1 share difference | -0.8333 | 0 | -0.0101 | 0 | 0 | 0.00034 | 0.0761 |
| origin HHI difference | -0.9291 | 0 | -0.0090 | 0 | 0 | 0 | 0.0417 |
| effective hubs difference | -2.06 | 0 | 0.75 | 0 | 1.49 | 4.91 | 34.22 |

Small networks produce coarse shares: with `N` routes, one route changes a share
by up to `1/N`. HHI=1 and top-1=1 for single-route networks are mathematically
correct but poor benchmarking evidence.

## 4. Minimum-size sensitivity

| Minimum routes | Airlines | Airline coverage | Route-presence coverage | Median top-1 | Median HHI | Median effective hubs | Maximum one-route share step |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 357 | 63.30% | 96.48% | 0.2750 | 0.12088 | 8.27 | 5 pp |
| 50 | 209 | 37.06% | 87.55% | 0.2312 | 0.09165 | 10.91 | 2 pp |
| 100 | 129 | 22.87% | 76.39% | 0.2179 | 0.07937 | 12.60 | 1 pp |

Recommendation:

- retain all airlines in canonical data;
- use 20 routes as a broad exploratory floor;
- use **50 routes as the default comparative/dashboard threshold** because it
  limits a one-route share change to 2 percentage points while retaining 87.55%
  of primary route presences;
- use 100 routes as a stricter sensitivity view, not the default.

The lower median HHI at higher thresholds partly reflects broader networks, so
rankings and correlations must always show the chosen threshold.

## 5. Correlation audit

Correlations below use airlines with at least 50 route presences unless stated
otherwise.

| Relationship | N | Pearson | Spearman | Interpretation |
|---|---:|---:|---:|---|
| network breadth vs top-1 origin share | 209 | -0.376 | -0.348 | moderate scale relationship, not identity |
| network breadth vs origin HHI | 209 | -0.402 | -0.473 | HHI is influenced by breadth but not determined by it |
| route count vs effective hubs | 209 | 0.768 | 0.473 | scale and effective hubs overlap substantially |
| international share vs median distance | 209 | 0.515 | 0.616 | extra geographic information, not causal |
| international share vs P90 distance | 209 | 0.492 | 0.566 | extra geographic information, not causal |
| country coverage vs median distance | 209 | 0.389 | 0.543 | moderate relationship |
| country coverage vs P90 distance | 209 | 0.600 | 0.697 | long-tail reach aligns more with country breadth |
| codeshare uplift vs primary breadth | 209 | 0.446 | 0.408 | uplift is not merely a network-size duplicate |
| top-1 origin share vs origin HHI | 209 | 0.968 | 0.965 | highly redundant concentration measures |
| effective hubs vs distinct origins | 209 | 0.410 | 0.190 | origin count is only a structural ceiling |
| airport destinations vs mean carriers per OD | 2,965 | 0.308 | 0.498 | connectivity breadth and carrier choice are distinct |

`effective_hubs` is exactly `1 / origin_airport_hhi`; they must not appear as
independent flagship KPIs. Top-1 share and HHI are also highly redundant, so use
top-1 for plain-language communication and effective hubs or HHI for analytical
detail.

The new HHI is not mechanically equal to network size. Three airlines with
exactly 74 route presences demonstrate this:

| Airline | Origins | Top-1 | HHI | Effective hubs |
|---|---:|---:|---:|---:|
| UTair-Express | 28 | 0.0946 | 0.05186 | 19.28 |
| NordStar Airlines | 30 | 0.2432 | 0.09423 | 10.61 |
| Tiger Airways | 38 | 0.5000 | 0.25676 | 3.89 |

The same route count supports materially different origin distributions.

## 6. Anomaly and boundary audit

Numerical latitude/longitude bounds all pass, but numeric validity is not enough:

- 483 source and 488 destination airport IDs do not match the airport dimension;
- among matched IDs, 538 source and 543 destination rows have raw route codes
  that match neither the dimension IATA nor ICAO;
- 1,075 raw rows have at least one such matched-ID/code inconsistency;
- for 450 source and 454 destination mismatches, the raw code maps to a
  different current airport ID;
- 975 of 52,296 primary route presences (1.864%) contain at least one endpoint
  code/dimension-code mismatch.

The most visible result is airport ID 5613: the row combines the name and
coordinates of Los Alamitos, California with city/country metadata for Solwesi,
Zambia. Four P0 records using raw code `SLI` then produce false distances near
16,000 km. Consequently, current distance, country-reach, airport-connectivity,
and carrier-diversity outputs require an endpoint-resolution quality flag and a
sensitivity rebuild before publication.

Recommended resolution order:

1. require raw route code to match dimension IATA or ICAO when possible;
2. when the raw code maps to a different airport ID, prefer a documented
   code-based resolution and flag the ID conflict;
3. keep unresolved historical codes as structural edges but exclude them from
   geography-dependent metrics;
4. publish included/excluded counts in the quality report.

Codeshare uplift is right-skewed but not controlled by one airline: 146 of 566
airlines have positive uplift; the largest airline contributes 8.80% of total
uplift and the top five contribute 30.88%. This supports carrier-level analysis
with both absolute and relative uplift, rather than only global totals.

## 7. Candidate insights

These are candidates, not final business conclusions. Geographic candidates are
conditional on resolving the endpoint inconsistency described above.

### Candidate 1 — Network scale and geographic reach are different dimensions

1. **Business question:** Does a larger route-presence network necessarily span
   more countries?
2. **Metric:** directed route presences, distinct countries, median/P90 distance.
3. **Evidence:** FR has 2,484 routes across 29 countries; TK has 534 routes
   across 104 countries. AF has 450 routes across 91 countries.
4. **Interpretation:** route breadth and country breadth rank airlines
   differently.
5. **Decision use:** screening comparable network archetypes and selecting
   peers for deeper review.
6. **Limitation:** historical presence only; geographic fields need endpoint
   resolution; no frequency or current network claim.
7. **Visual:** scatter of route presences vs distinct countries, with selected
   airline labels and a minimum-route filter.

### Candidate 2 — Hub dependence is not a network-size formula

1. **Business question:** Can similarly sized networks distribute routes very
   differently across origins?
2. **Metric:** top-1 origin share, origin HHI, effective hubs.
3. **Evidence:** at exactly 74 routes, UTair-Express has HHI 0.05186 and 19.28
   effective hubs; Tiger Airways has HHI 0.25676 and 3.89 effective hubs.
4. **Interpretation:** origin distribution adds information beyond route count.
5. **Decision use:** benchmark hub dependence among similarly sized historical
   networks.
6. **Limitation:** route-presence structure only; not schedule or traffic
   concentration.
7. **Visual:** airline-size vs origin-HHI scatter with a selected-airline origin
   share breakdown.

### Candidate 3 — Long-tail distance aligns more with country breadth than the median

1. **Business question:** Is broad country coverage associated with longer
   network reach?
2. **Metric:** distinct countries, median distance, P90 distance.
3. **Evidence:** for airlines with at least 50 routes, country coverage vs P90
   distance is Pearson 0.600/Spearman 0.697, compared with 0.389/0.543 for
   median distance.
4. **Interpretation:** international breadth is more visible in the long-distance
   tail than in the typical route.
5. **Decision use:** screen networks with broad long-haul reach for qualitative
   follow-up.
6. **Limitation:** correlation is not causal; distance metrics are provisional
   until endpoint resolution.
7. **Visual:** country count vs P90 distance scatter, with median distance in
   tooltip rather than as a second flagship chart.

### Candidate 4 — Codeshare-associated reach is material for a subset, not universal

1. **Business question:** Which listed networks expand most when codeshare rows
   are included?
2. **Metric:** route, airport, and country coverage uplift.
3. **Evidence:** 146 of 566 airlines have positive route uplift; 420 have none.
   UA adds 1,273 routes/247 airports/36 countries; KL adds 620 routes/260
   airports/33 countries. The top five airlines account for 30.88% of total
   uplift.
4. **Interpretation:** codeshare-associated reach is heterogeneous and not
   explained by one carrier alone.
5. **Decision use:** shortlist partnership-network cases for current-data
   validation.
6. **Limitation:** listed codeshares do not identify the actual operating
   carrier and are from 2014.
7. **Visual:** paired bars or dumbbells comparing non-codeshare and all-listed
   coverage, with absolute and relative uplift selectable.

### Candidate 5 — Connectivity breadth and carrier choice are related but distinct

1. **Business question:** Do airports with more destinations also offer more
   listed carriers per route?
2. **Metric:** outgoing destinations and mean listed carriers per outgoing OD.
3. **Evidence:** correlation is Pearson 0.308/Spearman 0.498. CDG has 237
   destinations and mean 1.56 carriers/OD; PEK has 204 and mean 2.00; LHR has
   170 and mean 1.90.
4. **Interpretation:** destination breadth alone does not summarize listed
   carrier choice.
5. **Decision use:** screen airports that combine reach breadth with carrier
   choice for regional-connectivity benchmarking.
6. **Limitation:** no service frequency, capacity, traffic, or current market
   evidence; airport identity quality must be resolved.
7. **Visual:** airport scatter with destinations on X and mean carrier count on
   Y; size may represent international destination count.

### Candidate 6 — Most directed ODs have limited listed-carrier choice

1. **Business question:** How widely distributed is listed-carrier choice across
   directed airport pairs?
2. **Metric:** listed_carrier_count.
3. **Evidence:** 22,610 of 33,854 ODs (66.79%) have one listed carrier; 12.59%
   have at least three; the maximum is 10.
4. **Interpretation:** multi-carrier listing is concentrated in a minority of
   historical OD records.
5. **Decision use:** identify OD groups for further validation with schedule and
   capacity data.
6. **Limitation:** a single listed carrier is not monopoly; codeshares are
   excluded and the snapshot is historical.
7. **Visual:** compact distribution of carrier counts plus a drill-through OD
   table.

### Candidate 7 — Codeshare inclusion can change apparent hub distribution

1. **Business question:** Does the all-listed network change apparent origin
   concentration?
2. **Metric:** top-1 difference, HHI difference, effective-hubs difference.
3. **Evidence:** UA changes from HHI 0.03773 to 0.02673 and gains 10.91
   effective hubs when all-listed rows are included. Across all airlines the
   median difference is zero, but P90 effective-hubs uplift is 1.49 and the
   maximum is 34.22.
4. **Interpretation:** the effect is substantial for a subset and negligible for
   most carriers.
5. **Decision use:** flag networks where partnership-associated reach changes
   structural benchmarking.
6. **Limitation:** all-listed is not an operating network and effective hubs is
   the inverse of HHI, not an independent KPI.
7. **Visual:** selected-airline before/after slope chart, supported by an uplift
   distribution.

## 8. Three recommended flagship stories

1. **Same size, different hub structure** — strongest validated structural
   story and not mechanically determined by route count.
2. **Network breadth vs geographic reach** — strategically legible, but publish
   only after endpoint resolution.
3. **Codeshare-associated reach sensitivity** — clearly framed as historical
   screening, using both absolute and relative uplift.

Carrier choice and airport connectivity should support the third/fourth report
pages rather than compete as additional executive KPIs.

## 9. Decision-support boundaries

### Airline network strategy analyst

- **Directly supported:** historical directed-route breadth, country coverage,
  origin concentration, reciprocity, codeshare sensitivity.
- **Screening/benchmarking:** peer networks of similar size; high/low hub
  dependence; long-tail geographic reach.
- **Requires additional data:** current strategy, schedule intensity, capacity,
  demand, economics, operational resilience.

### Airport or regional connectivity analyst

- **Directly supported:** historical destination breadth, origin breadth,
  listed-airline counts, international connection breadth, reciprocity.
- **Screening/benchmarking:** airports with similar destination breadth but
  different listed-carrier choice.
- **Requires additional data:** passenger accessibility, service quality,
  frequency, seats, current airline presence, economic impact.

### Partnership / codeshare strategy analyst

- **Directly supported:** historical difference between non-codeshare proxy and
  all-listed route presence.
- **Screening/benchmarking:** airlines with large route/airport/country uplift or
  changed hub-distribution metrics.
- **Requires additional data:** current agreements, actual operating carrier,
  schedules, traffic flows, revenue contribution, partnership performance.

## 10. Readiness conclusion

Metric formulas and table transformations are reproducible and independently
validated. The project is **not yet ready for final Dashboard reconstruction**
because:

1. airport endpoint code/ID inconsistencies can corrupt geography and labels;
2. a stable `airline_key` and a 566-row airline dimension are not exported;
3. an airline-origin distribution table is needed for explainable hub drilldown;
4. threshold and quality-status fields should be model inputs, not hidden report
   logic.

After those focused Phase 2.1 corrections, the project will be ready to rebuild
the Dashboard without changing its approved analytical scope.
