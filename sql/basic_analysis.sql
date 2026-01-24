--find out which routes are most popular
SELECT
  source_iata,
  destination_iata,
  COUNT(*) AS route_count
FROM routes_enriched
WHERE source_iata IS NOT NULL
  AND destination_iata IS NOT NULL
GROUP BY source_iata, destination_iata
ORDER BY route_count DESC
LIMIT 20;

--check data quality
SELECT
  COUNT(*) AS total_routes,
  SUM(CASE WHEN source_iata IS NULL OR destination_iata IS NULL THEN 1 ELSE 0 END) AS routes_with_missing_iata
FROM routes_enriched;

--most busy depreture airports(top 20)
SELECT
  source_iata,
  COUNT(*) AS departures
FROM routes_enriched
WHERE source_iata IS NOT NULL
GROUP BY source_iata
ORDER BY departures DESC
LIMIT 20;

--most busy depreture airports(top 20)
SELECT
  destination_iata,
  COUNT(*) AS arrivals
FROM routes_enriched
WHERE destination_iata IS NOT NULL
GROUP BY destination_iata
ORDER BY arrivals DESC
LIMIT 20;
