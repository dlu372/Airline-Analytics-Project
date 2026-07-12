import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {csvParse, autoType} from "d3-dsv";

const analytics = new URL("../../data/analytics/", import.meta.url);

async function loadCsv(name) {
  return csvParse(await readFile(new URL(name, analytics), "utf8"), autoType);
}

const [summary, geography, hubs, dimension, codeshare, quality] = await Promise.all([
  loadCsv("airline_network_summary.csv"),
  loadCsv("airline_geographic_reach.csv"),
  loadCsv("airline_hub_dependence.csv"),
  loadCsv("dim_airline.csv"),
  loadCsv("codeshare_sensitivity.csv"),
  JSON.parse(await readFile(new URL("data_quality.json", analytics), "utf8"))
]);

const byKey = (rows) => new Map(rows.map((d) => [d.airline_key, d]));
const geographyByKey = byKey(geography);
const hubsByKey = byKey(hubs);
const dimensionByKey = byKey(dimension);

const airlines = summary.map((network) => {
  const geo = geographyByKey.get(network.airline_key);
  const hub = hubsByKey.get(network.airline_key);
  const dim = dimensionByKey.get(network.airline_key);
  assert(geo && hub && dim, `Incomplete airline join for ${network.airline_key}`);
  return {
    airline_key: network.airline_key,
    airline_code: network.airline_code,
    airline_name: network.airline_name ?? network.airline_code,
    airline_country: network.airline_country,
    active_status: dim.active_status,
    directed_route_presences: network.directed_route_presences,
    distinct_origin_airports: network.distinct_origin_airports,
    distinct_destination_airports: network.distinct_destination_airports,
    reciprocal_route_share: network.reciprocal_route_share,
    comparison_threshold_50: network.directed_route_presences >= 50,
    dashboard_default_eligible: network.directed_route_presences >= 50,
    distinct_country_count: geo.distinct_country_count,
    international_route_presence_share: geo.international_route_presence_share,
    median_route_distance_km: geo.median_route_distance_km,
    p90_route_distance_km: geo.p90_route_distance_km,
    valid_distance_route_presences: geo.valid_distance_route_presences,
    invalid_or_missing_distance_route_presences: geo.invalid_or_missing_distance_route_presences,
    top1_origin_share: hub.top1_origin_share,
    top3_origin_share: hub.top3_origin_share,
    origin_airport_hhi: hub.origin_airport_hhi,
    effective_hubs: hub.effective_hubs
  };
});

const getAirline = (code) => {
  const row = airlines.find((d) => d.airline_code === code);
  assert(row, `Missing airline ${code}`);
  return row;
};
const getByName = (name) => {
  const row = airlines.find((d) => d.airline_name === name);
  assert(row, `Missing airline ${name}`);
  return row;
};
const getCodeshare = (code) => {
  const row = codeshare.find((d) => d.airline_code === code);
  assert(row, `Missing codeshare airline ${code}`);
  return row;
};
const near = (actual, expected, tolerance = 0.005) =>
  assert(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);

const fr = getAirline("FR");
const tk = getAirline("TK");
const af = getAirline("AF");
assert.deepEqual([fr.directed_route_presences, fr.distinct_country_count], [2484, 29]);
assert.deepEqual([tk.directed_route_presences, tk.distinct_country_count], [534, 104]);
assert.deepEqual([af.directed_route_presences, af.distinct_country_count], [450, 91]);

const utair = getByName("UTair-Express");
const tiger = getByName("Tiger Airways");
assert.equal(utair.directed_route_presences, 74);
assert.equal(tiger.directed_route_presences, 74);
near(utair.effective_hubs, 19.28, 0.01);
near(tiger.effective_hubs, 3.89, 0.01);

const ua = getCodeshare("UA");
const kl = getCodeshare("KL");
assert.deepEqual(
  [ua.route_presence_uplift, ua.airport_coverage_uplift, ua.country_coverage_uplift],
  [1273, 247, 36]
);
assert.deepEqual(
  [kl.route_presence_uplift, kl.airport_coverage_uplift, kl.country_coverage_uplift],
  [620, 260, 33]
);

const positiveUplift = codeshare.filter((d) => d.route_presence_uplift > 0).length;
const zeroUplift = codeshare.filter((d) => d.route_presence_uplift === 0).length;
const totalUplift = codeshare.reduce((sum, d) => sum + d.route_presence_uplift, 0);
const topFiveShare = [...codeshare]
  .sort((a, b) => b.route_presence_uplift - a.route_presence_uplift)
  .slice(0, 5)
  .reduce((sum, d) => sum + d.route_presence_uplift, 0) / totalUplift;
assert.deepEqual([positiveUplift, zeroUplift], [146, 420]);
near(topFiveShare, 0.3088, 0.00005);

const metrics = quality.quality_metrics;
const eligibleAirlines = airlines.filter((d) => d.dashboard_default_eligible);

const payload = {
  meta: {
    dataset: quality.dataset,
    analysis_unit: quality.analysis_unit,
    primary_network: quality.primary_network,
    airline_count: dimension.length,
    airline_comparison_count: eligibleAirlines.length,
    non_codeshare_route_presences: metrics.non_codeshare_valid_directed_route_presences,
    geographic_route_presences: metrics.distance_valid_non_codeshare_route_presences,
    geographic_excluded_route_presences: metrics.geographic_excluded_non_codeshare_route_presences,
    endpoint_route_rows_eligible: metrics.canonical_geographic_route_rows,
    endpoint_route_rows_total: metrics.raw_route_row_count,
    airport_5613_geographic_eligible_rows: metrics.airport_5613_geographic_eligible_rows,
    endpoint_status_counts: metrics.endpoint_resolution_status_counts,
    positive_codeshare_uplift_airlines: positiveUplift,
    zero_codeshare_uplift_airlines: zeroUplift,
    top_five_codeshare_uplift_share: topFiveShare
  },
  airlines,
  codeshare,
  flagships: {
    reach: [fr, tk, af],
    hubs: [utair, tiger],
    codeshare: [ua, kl]
  }
};

process.stdout.write(JSON.stringify(payload));
