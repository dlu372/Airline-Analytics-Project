# Data dictionary

## Clean and enriched tables

### `airports_clean`

One row per OpenFlights airport record. `airport_id` is the primary key;
latitude and longitude are decimal degrees.

### `airlines_clean`

One row per OpenFlights airline record. `airline_id` is the primary key.
`active` is retained as historical source metadata and is not treated as a
current operational status.

### `routes_clean`

One row per raw directional route record. `is_codeshare` is true when the raw
codeshare field is `Y`.

### `routes_enriched`

Routes joined to source airport, destination airport, and airline dimensions.
`airline_key` uses `airline_id` where available and falls back to the listed
airline code when the ID is missing.

## Analytics tables

### `airline_network_summary`

One row per airline in the primary non-codeshare network. Counts route-presence
breadth, airport/country coverage, domestic/international shares, reciprocal
route share, and the codeshare share observed in the all-listed network.

### `airline_hub_dependence`

One row per airline. `top1_origin_share`, `top3_origin_share`, and
`origin_airport_hhi` are calculated across origin airports. `effective_hubs` is
the inverse of origin HHI. Values are stored without presentation rounding.

### `airline_geographic_reach`

One row per airline with mean, median, and 90th-percentile great-circle route
distance, distance validity counts, country coverage, and route-presence shares.

### `airport_connectivity`

One row per airport present in the primary network. Connectivity fields count
distinct airports or listed airlines, not flights or passengers.

### `route_carrier_diversity`

One row per directed airport pair in the primary network. `listed_carrier_count`
counts distinct listed airlines; `listed_carrier_names` is a semicolon-separated
display field. `codeshare_included` is false for this Phase 2 primary table.

### `codeshare_sensitivity`

One row per airline in the all-listed network. It compares route, airport,
country, and origin-distribution metrics between the non-codeshare proxy and the
all-listed network. Uplift/difference fields are all-listed minus non-codeshare.

## Canonical database

`data/analytics/airline_network_analytics.sqlite` is generated from scratch by
the pipeline and contains the clean, enriched, route-presence, quality, and six
analytics tables. Databases under `legacy/database/` are not pipeline inputs.
