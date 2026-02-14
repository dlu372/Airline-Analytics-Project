CREATE VIEW IF NOT EXISTS v_routes AS
SELECT *
FROM routes_enriched
WHERE source_iata IS NOT NULL
  AND destination_iata IS NOT NULL
  AND source_iata <> ''
  AND destination_iata <> '';

-- Airport Hub Index
SELECT
  source_iata AS airport,
  COUNT(*) AS departures,
  COUNT(DISTINCT destination_iata) AS unique_destinations,
  ROUND(1.0 * COUNT(*) / COUNT(DISTINCT destination_iata), 2) AS avg_freq_per_destination
FROM v_routes
GROUP BY source_iata
HAVING departures >= 200
ORDER BY unique_destinations DESC, departures DESC
LIMIT 30;

--Bidirectional strong connection
WITH pair AS (
  SELECT
    CASE WHEN source_iata < destination_iata THEN source_iata ELSE destination_iata END AS a,
    CASE WHEN source_iata < destination_iata THEN destination_iata ELSE source_iata END AS b
  FROM v_routes
),
cnt AS (
  SELECT a, b, COUNT(*) AS total_routes
  FROM pair
  GROUP BY a, b
)
SELECT *
FROM cnt
ORDER BY total_routes DESC
LIMIT 30;

--International INDEX
SELECT
  source_iata AS airport,
  COUNT(*) AS departures,
  SUM(CASE WHEN source_country <> destination_country THEN 1 ELSE 0 END) AS intl_departures,
  ROUND(100.0 * SUM(CASE WHEN source_country <> destination_country THEN 1 ELSE 0 END) / COUNT(*), 1) AS intl_share_pct
FROM v_routes
WHERE source_country IS NOT NULL AND destination_country IS NOT NULL
GROUP BY source_iata
HAVING departures >= 200
ORDER BY intl_share_pct DESC, departures DESC
LIMIT 30;

--Identification of "high-risk single-point airports"
WITH route_airlines AS (
  SELECT
    source_iata,
    destination_iata,
    COUNT(DISTINCT airline) AS airline_cnt
  FROM v_routes
  GROUP BY source_iata, destination_iata
),
airport_routes AS (
  SELECT
    source_iata AS airport,
    COUNT(*) AS total_routes,
    SUM(CASE WHEN airline_cnt = 1 THEN 1 ELSE 0 END) AS monopoly_routes
  FROM route_airlines
  GROUP BY source_iata
)
SELECT
  airport,
  total_routes,
  monopoly_routes,
  ROUND(100.0 * monopoly_routes / total_routes, 1) AS monopoly_share_pct
FROM airport_routes
WHERE total_routes >= 200
ORDER BY monopoly_share_pct DESC, total_routes DESC
LIMIT 30;

--A profile of airlines' "network breadth vs. focus"
SELECT
  airline,
  COUNT(*) AS routes,
  COUNT(DISTINCT source_iata) AS origin_airports,
  COUNT(DISTINCT destination_iata) AS dest_airports,
  COUNT(DISTINCT source_country) AS origin_countries,
  COUNT(DISTINCT destination_country) AS dest_countries
FROM v_routes
GROUP BY airline
HAVING routes >= 200
ORDER BY dest_countries DESC, routes DESC
LIMIT 30;

--Equipment data is used as a proxy for aircraft type and fleet complexity. 
--This analysis does not assume exact aircraft capacity but focuses on relative operational patterns across airlines.
SELECT
  airline,
  COUNT(*) AS routes,
  COUNT(DISTINCT equipment) AS equipment_variants
FROM v_routes
WHERE equipment IS NOT NULL AND equipment <> ''
GROUP BY airline
HAVING routes >= 200
ORDER BY equipment_variants DESC;


--stage03
--Are airline route networks concentrated on a small number of routes, or distributed more evenly across many routes?

--Build a "Basic Table of Route Frequency" (once)
CREATE VIEW IF NOT EXISTS v_route_frequency AS
SELECT
  airline,
  source_iata,
  destination_iata,
  COUNT(*) AS route_count
FROM v_routes
GROUP BY airline, source_iata, destination_iata;

--Calculate the "total route frequency" of each airline (once)
CREATE VIEW IF NOT EXISTS v_airline_total_routes AS
SELECT
  airline,
  SUM(route_count) AS total_route_count
FROM v_route_frequency
GROUP BY airline;

--Calculate the "Proportion of Top N Routes" (repeat this)
WITH ranked_routes AS (
  SELECT
    r.airline,
    r.source_iata,
    r.destination_iata,
    r.route_count,
    ROW_NUMBER() OVER (
      PARTITION BY r.airline
      ORDER BY r.route_count DESC
    ) AS rn
  FROM v_route_frequency r
)
SELECT
  airline,
  SUM(route_count) AS top10_route_count
FROM ranked_routes
WHERE rn <= 10
GROUP BY airline;

WITH ranked_routes AS (
  SELECT
    r.airline,
    r.route_count,
    ROW_NUMBER() OVER (
      PARTITION BY r.airline
      ORDER BY r.route_count DESC
    ) AS rn
  FROM v_route_frequency r
),
top10 AS (
  SELECT
    airline,
    SUM(route_count) AS top10_route_count
  FROM ranked_routes
  WHERE rn <= 10
  GROUP BY airline
)

SELECT
  t.airline,
  t.top10_route_count,
  a.total_route_count,
  ROUND(100.0 * t.top10_route_count / a.total_route_count, 1) AS top10_share_pct
FROM top10 t
JOIN v_airline_total_routes a
  ON t.airline = a.airline
ORDER BY top10_share_pct DESC;

--HHI (Herfindahl-Hirschman Index) is a commonly used measure of market concentration.
WITH route_share AS (
  SELECT
    f.airline,
    f.route_count,
    1.0 * f.route_count / t.total_route_count AS share
  FROM v_route_frequency f
  JOIN v_airline_total_routes t
    ON f.airline = t.airline
),
hhi AS (
  SELECT
    airline,
    ROUND(SUM(share * share), 4) AS hhi
  FROM route_share
  GROUP BY airline
),
ranked_routes AS (
  SELECT
    r.airline,
    r.route_count,
    ROW_NUMBER() OVER (
      PARTITION BY r.airline
      ORDER BY r.route_count DESC
    ) AS rn
  FROM v_route_frequency r
),
top10 AS (
  SELECT
    airline,
    SUM(route_count) AS top10_route_count
  FROM ranked_routes
  WHERE rn <= 10
  GROUP BY airline
),

-- First, spell the final fields to be displayed as "base"
base AS (
  SELECT
    a.airline,
    a.total_route_count,
    ROUND(100.0 * top10.top10_route_count / a.total_route_count, 1) AS top10_share_pct,
    hhi.hhi
  FROM v_airline_total_routes a
  JOIN top10 ON top10.airline = a.airline
  JOIN hhi  ON hhi.airline  = a.airline
  WHERE a.total_route_count >= 200
),

-- Calculate the quantile (0 to 1) of each airline in the overall population
ranked AS (
  SELECT
    *,
    PERCENT_RANK() OVER (ORDER BY hhi) AS pr
  FROM base
)

-- The final output: CASE no longer uses a fixed threshold but pr
SELECT
  airline,
  total_route_count,
  top10_share_pct,
  hhi,
  CASE
    WHEN pr >= 0.80 THEN 'Highly concentrated'        -- top 20%
    WHEN pr >= 0.50 THEN 'Moderately concentrated'    -- 50%~80%
    ELSE 'Distributed'                                -- bottom 50%
  END AS concentration_label
FROM ranked
ORDER BY hhi DESC;