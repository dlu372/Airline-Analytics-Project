# Power BI dashboard plan

## Status

Do not rebuild the PBIX until the Phase 2.1 blockers in
`docs/insight_validation.md` are resolved: endpoint identity quality, exported
airline keys/dimension, and an airline-origin detail table. The current PBIX is
a legacy concentration report and should not be extended.

Every page must display:

> OpenFlights 2014 historical route-presence snapshot. Counts are route
> presences, not flights, passengers, capacity, revenue, profitability, or
> current market activity. Non-codeshare routes are an operating-network proxy.

The default airline-comparison population should use at least 50 primary route
presences. A methodology control may expose 20/50/100 sensitivity views, but the
underlying model must retain every airline.

## Recommended data model

Use a small star/snowflake model rather than joining CSVs by airline name:

- `dim_airline`: union of all 566 airline keys, with ID, code, name, country,
  active flag, and `has_non_codeshare_network`;
- `dim_airport`: one row per resolved airport key with endpoint-quality status;
- airline facts: network summary, hub dependence, geographic reach, codeshare
  sensitivity;
- airport fact: airport connectivity;
- directed-OD fact: route carrier diversity;
- airline-origin fact: origin route count/share for hub drilldown.

Relationships should use `airline_key` and resolved airport keys. Do not join on
airline name, IATA alone, or nullable airline ID. The two codeshare-only airlines
remain in `dim_airline` and have blank primary-network measures.

## Page 1 — Executive Overview

**Business question:** What does the historical network snapshot cover, and
which structural comparisons are reliable?

**KPIs (2–4):**

- primary directed route presences;
- airlines above the selected comparison threshold;
- resolved airports / endpoint-quality pass rate;
- directed OD pairs.

**Visuals:**

- one breadth-vs-country-coverage scatter;
- one compact distribution of route-presence network size;
- one methodology/quality summary, not a decorative KPI grid.

**Fields:** directed_route_presences, distinct_countries, airline_name,
airline_key, comparison-threshold flag, endpoint-quality metrics.

**Takeaway:** Network scale and geographic breadth describe different aspects
of the historical route-presence network.

**Required limitation:** rankings are historical route presences and depend on
the selected minimum-size threshold.

## Page 2 — Airline Network Reach

**Business question:** How do airlines differ in route breadth, country reach,
international share, and distance profile?

**KPIs:**

- directed route presences;
- distinct airports and countries;
- international route-presence share;
- P90 route distance.

**Visuals:**

- route count vs distinct countries scatter;
- country count vs P90 distance scatter;
- selected-airline profile table with median and P90 distance.

**Fields:** airline_network_summary and airline_geographic_reach fields joined
through airline_key.

**Takeaway:** A larger route-presence network does not automatically have the
widest country reach.

**Required limitation:** distance and country metrics must exclude unresolved
endpoint records; route distance is not passenger journey distance.

## Page 3 — Hub Dependence

**Business question:** How concentrated is each airline's historical route
presence across origin airports?

**KPIs:**

- top-1 origin share;
- top-3 origin share;
- origin HHI or effective hubs, not both as independent headline KPIs;
- distinct origins.

**Visuals:**

- route count vs origin HHI scatter with size-peer comparison;
- selected-airline origin-share bar chart from the proposed airline-origin fact;
- compact peer table showing route count, top-1, HHI, and effective hubs.

**Fields:** airline_hub_dependence plus airline-origin route count/share.

**Takeaway:** Airlines of similar network size can distribute route presences
very differently across origins.

**Required limitation:** hub dependence describes structural route presence,
not flight, seat, passenger, or revenue concentration.

## Page 4 — Airport Connectivity & Carrier Choice

**Business question:** Which airports combine destination breadth with greater
listed-carrier choice?

**KPIs:**

- outgoing distinct destinations;
- incoming distinct origins;
- international destination count;
- mean listed carriers per outgoing directed OD.

**Visuals:**

- airport connectivity vs mean carrier-choice scatter;
- selected-airport top directed ODs by listed carrier count;
- carrier-count distribution for the filtered airport/region.

**Fields:** airport_connectivity, route_carrier_diversity, dim_airport, source
and destination resolved keys.

**Takeaway:** Destination breadth and listed-carrier choice are related but not
interchangeable measures.

**Required limitation:** listed carrier count is not market share, service
frequency, passenger choice, or monopoly evidence.

## Page 5 — Codeshare Sensitivity & Methodology

**Business question:** How much does an airline's listed network change when
codeshare records are included?

**KPIs:**

- route-presence uplift;
- airport coverage uplift;
- country coverage uplift;
- top-1 or origin-HHI difference.

**Visuals:**

- non-codeshare vs all-listed dumbbell chart for selected carriers;
- distribution of absolute and relative route uplift;
- methodology panel defining all-listed minus non-codeshare.

**Fields:** all codeshare_sensitivity fields plus calculated relative uplift and
`has_non_codeshare_network`.

**Takeaway:** Codeshare-associated reach is material for a subset of airlines
and negligible for most.

**Required limitation:** neither view identifies the actual operating carrier;
the result is historical screening only.

## Visual discipline

- Keep each page to one main question and two or three analytical visuals.
- Use airline code only as a compact label; show airline name in titles/tooltips.
- Do not show top-1, HHI, and effective hubs as three independent signals.
- Do not add causal language to correlation charts.
- Never use frequency, departures, arrivals, busiest, market share, monopoly,
  passenger demand, profitability, or current-strategy wording.
