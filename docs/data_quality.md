# Data quality controls

The pipeline fails when the raw file checksum changes, when the expected 67,663
route rows are not present, when airport or airline IDs are duplicated in their
dimensions, or when enrichment changes the route row count.

Every run records the following in `data/analytics/data_quality.json` and in the
SQLite `data_quality_metrics` table:

- raw and enriched route row counts
- airport and airline ID uniqueness
- airline ID match count and rate
- missing source and destination IATA counts
- missing airport-dimension matches
- codeshare count and share
- duplicate airline–origin–destination keys
- source-equals-destination count
- missing or invalid coordinates
- valid all-listed and non-codeshare route-presence counts
- valid non-codeshare distance count

The raw files are protected by `data/raw/checksums.sha256`. The pipeline does not
modify them.

## Known limitations

- The route data is historical and ceased receiving source updates in 2014.
- A codeshare flag does not identify the actual operating carrier.
- Some route rows have missing or unmatched airport/airline IDs.
- IATA codes are display attributes; airport IDs are the primary join keys.
- Equipment strings can contain multiple codes and are not used as a flagship
  metric in Phase 2.
