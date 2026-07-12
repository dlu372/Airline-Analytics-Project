import * as Plot from "npm:@observablehq/plot";

const accent = "var(--theme-foreground-focus)";
const ink = "var(--theme-foreground)";
const muted = "var(--theme-foreground-muted)";
const faint = "var(--theme-foreground-faint)";

const airlineLabel = (d) => `${d.airline_name} (${d.airline_code ?? "—"})`;

export function reachChart(data, selectedKey, {width = 900} = {}) {
  const highlighted = new Set([selectedKey, ...data.flagships.reach.map((d) => d.airline_key)]);
  const peers = data.airlines.filter((d) => d.dashboard_default_eligible);
  const labels = peers.filter((d) => highlighted.has(d.airline_key));
  return Plot.plot({
    width,
    height: width < 560 ? 390 : 470,
    marginLeft: 58,
    marginBottom: 48,
    x: {type: "log", grid: true, label: "Directed route presences (log scale) →", ticks: 6},
    y: {grid: true, label: "Countries reached →", domain: [0, 112]},
    marks: [
      Plot.dot(peers, {
        x: "directed_route_presences",
        y: "distinct_country_count",
        r: 4.5,
        fill: muted,
        fillOpacity: 0.32,
        stroke: faint,
        tip: true,
        channels: {
          Airline: airlineLabel,
          Routes: "directed_route_presences",
          Countries: "distinct_country_count",
          "Median distance (km)": (d) => Math.round(d.median_route_distance_km)
        }
      }),
      Plot.dot(labels, {
        x: "directed_route_presences",
        y: "distinct_country_count",
        r: (d) => d.airline_key === selectedKey ? 8 : 6,
        fill: (d) => d.airline_key === selectedKey ? accent : ink,
        stroke: "var(--theme-background)",
        strokeWidth: 2,
        tip: true,
        channels: {Airline: airlineLabel, Routes: "directed_route_presences", Countries: "distinct_country_count"}
      }),
      Plot.text(labels, {
        x: "directed_route_presences",
        y: "distinct_country_count",
        text: "airline_code",
        dx: 10,
        dy: -9,
        textAnchor: "start",
        fontWeight: 600,
        fill: ink
      }),
      Plot.frame({stroke: faint})
    ]
  });
}

export function hubChart(data, selectedKey, {width = 900} = {}) {
  const peers = data.airlines.filter((d) => d.dashboard_default_eligible);
  const flagships = data.flagships.hubs;
  const flagshipKeys = new Set(flagships.map((d) => d.airline_key));
  const selected = peers.filter((d) => d.airline_key === selectedKey && !flagshipKeys.has(d.airline_key));
  return Plot.plot({
    width,
    height: width < 560 ? 390 : 460,
    marginLeft: 58,
    marginBottom: 48,
    x: {type: "log", grid: true, label: "Directed route presences (log scale) →", ticks: 6},
    y: {grid: true, label: "Effective hubs →"},
    marks: [
      Plot.dot(peers, {
        x: "directed_route_presences",
        y: "effective_hubs",
        r: 4.5,
        fill: muted,
        fillOpacity: 0.3,
        stroke: faint,
        tip: true,
        channels: {
          Airline: airlineLabel,
          Routes: "directed_route_presences",
          "Effective hubs": (d) => d.effective_hubs.toFixed(2),
          "Top origin share": (d) => `${(d.top1_origin_share * 100).toFixed(1)}%`
        }
      }),
      Plot.dot(selected, {
        x: "directed_route_presences",
        y: "effective_hubs",
        r: 7,
        fill: "var(--theme-background)",
        stroke: accent,
        strokeWidth: 2,
        tip: true,
        channels: {Airline: airlineLabel, Routes: "directed_route_presences", "Effective hubs": (d) => d.effective_hubs.toFixed(2)}
      }),
      Plot.text(selected, {
        x: "directed_route_presences",
        y: "effective_hubs",
        text: "airline_code",
        dx: 10,
        dy: -8,
        textAnchor: "start",
        fill: muted
      }),
      Plot.dot(flagships, {
        x: "directed_route_presences",
        y: "effective_hubs",
        r: 8,
        fill: accent,
        stroke: "var(--theme-background)",
        strokeWidth: 2,
        tip: true,
        channels: {Airline: airlineLabel, Routes: "directed_route_presences", "Effective hubs": (d) => d.effective_hubs.toFixed(2)}
      }),
      Plot.text(flagships, {
        x: "directed_route_presences",
        y: "effective_hubs",
        text: (d) => width < 560 ? d.airline_code : d.airline_name,
        dx: 12,
        dy: width < 560 ? -18 : -12,
        textAnchor: "start",
        fontWeight: 600,
        fontSize: width < 560 ? 10 : 12,
        fill: ink,
        stroke: "var(--theme-background)",
        strokeWidth: 4,
        paintOrder: "stroke"
      }),
      Plot.text(flagships, {
        x: "directed_route_presences",
        y: "effective_hubs",
        text: (d) => width < 560
          ? `${d.directed_route_presences} · ${d.effective_hubs.toFixed(2)} hubs`
          : `${d.directed_route_presences} routes · ${d.effective_hubs.toFixed(2)} hubs`,
        dx: 12,
        dy: width < 560 ? -4 : 5,
        textAnchor: "start",
        fontSize: width < 560 ? 9 : 11,
        fill: muted,
        stroke: "var(--theme-background)",
        strokeWidth: 4,
        paintOrder: "stroke"
      }),
      Plot.frame({stroke: faint})
    ]
  });
}

export function codeshareChart(data, selectedKey, {width = 900} = {}) {
  const selected = data.codeshare.find((d) => d.airline_key === selectedKey);
  const top = [...data.codeshare]
    .filter((d) => d.route_presence_uplift > 0)
    .sort((a, b) => b.route_presence_uplift - a.route_presence_uplift)
    .slice(0, 10);
  if (selected?.route_presence_uplift > 0 && !top.some((d) => d.airline_key === selectedKey)) {
    top.pop();
    top.push(selected);
  }
  top.sort((a, b) => a.route_presence_uplift - b.route_presence_uplift);
  const chartRows = top.map((d) => ({
    ...d,
    chart_label: `${d.airline_code} · ${d.airline_name ?? d.airline_code}`
  }));
  return Plot.plot({
    width,
    height: width < 560 ? 420 : 470,
    marginLeft: width < 560 ? 76 : 218,
    marginRight: 46,
    x: {grid: true, label: "Additional listed route presences when codeshares are included →"},
    y: {
      label: null,
      tickFormat: (label) => width < 650 ? label.split(" · ")[0] : label
    },
    marks: [
      Plot.barX(chartRows, {
        x: "route_presence_uplift",
        y: "chart_label",
        fill: (d) => d.airline_key === selectedKey ? accent : ink,
        fillOpacity: (d) => d.airline_key === selectedKey ? 1 : 0.72,
        tip: {
          format: {
            Airline: true,
            "Route uplift": true,
            "Airport uplift": true,
            "Country uplift": true,
            x: false,
            y: false,
            chart_label: false,
            fill: false,
            fillOpacity: false
          }
        },
        channels: {
          Airline: (d) => `${d.airline_name ?? d.airline_code} (${d.airline_code})`,
          "Route uplift": "route_presence_uplift",
          "Airport uplift": "airport_coverage_uplift",
          "Country uplift": "country_coverage_uplift"
        }
      }),
      Plot.text(chartRows, {
        x: "route_presence_uplift",
        y: "chart_label",
        text: (d) => `+${d.route_presence_uplift.toLocaleString("en-US")}`,
        dx: 6,
        textAnchor: "start",
        fill: ink,
        fontWeight: 600
      }),
      Plot.ruleX([0], {stroke: faint})
    ]
  });
}
