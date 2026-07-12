---
title: Airline Network Structure & Connectivity Analytics
toc: false
---

```js
import {reachChart, hubChart, codeshareChart} from "./components/charts.js";
const data = await FileAttachment("./data/dashboard.json").json();
const eligibleAirlines = data.airlines
  .filter((d) => d.dashboard_default_eligible)
  .sort((a, b) => a.airline_name.localeCompare(b.airline_name));
const airlineLabels = new Map(eligibleAirlines.map((d) => [d.airline_key, `${d.airline_name} (${d.airline_code ?? "—"})`]));
const number = (value) => value?.toLocaleString("en-US");
const percent = (value, digits = 1) => value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
```

<header class="hero">
  <div>
    <div class="eyebrow">OpenFlights · 2014 historical snapshot</div>
    <h1>How airline networks connect places.</h1>
    <p class="hero-deck">A route-presence view of network breadth, geographic reach, hub dependence and codeshare-associated reach—built for structural comparison, not claims about traffic or commercial performance.</p>
    <div class="author-line">
      <span><strong>Built by Di Lu</strong></span>
      <span>Information Systems &amp; Business Analytics · University of Auckland</span>
      <a href="https://github.com/dlu372">GitHub</a>
    </div>
  </div>
  <aside class="hero-side">
    <p><strong>Unit of analysis</strong><br>One listed airline–origin–destination route presence.</p>
    <p>Presence indicates that a directed route was listed in the historical dataset. It does not measure flights, seats, passengers, demand, revenue or current activity.</p>
    <div class="link-row">
      <a class="text-link" href="#methodology">View methodology</a>
      <a class="text-link" href="https://github.com/dlu372/Airline-Analytics-Project">View source code</a>
    </div>
  </aside>
</header>

<div class="control-bar">
  <div class="control-copy">
    <div class="section-kicker" id="overview-title">Executive overview</div>
    <p>Default comparisons include airlines with at least 50 non-codeshare route presences. Inactive airlines remain because the analysis describes a historical snapshot.</p>
  </div>
</div>

```js
const selectedAirlineKey = view(Inputs.select(eligibleAirlines.map((d) => d.airline_key), {
  label: "Highlight an airline",
  value: data.flagships.reach.find((d) => d.airline_code === "TK").airline_key,
  format: (key) => airlineLabels.get(key)
}));
```
```js
const selectedAirline = data.airlines.find((d) => d.airline_key === selectedAirlineKey);
const selectedCodeshare = data.codeshare.find((d) => d.airline_key === selectedAirlineKey);
```

<section aria-labelledby="overview-title">
  <div class="overview-grid">
    <div class="overview-stat"><span class="section-kicker">Primary network</span><span class="value">${number(data.meta.non_codeshare_route_presences)}</span><span class="label">non-codeshare directed route presences</span></div>
    <div class="overview-stat"><span class="section-kicker">Comparison set</span><span class="value">${number(data.meta.airline_comparison_count)}</span><span class="label">airlines at the default ≥50 threshold</span></div>
    <div class="overview-stat"><span class="section-kicker">Geography ready</span><span class="value">${percent(data.meta.geographic_route_presences / data.meta.non_codeshare_route_presences, 1)}</span><span class="label">of primary route presences eligible for geographic metrics</span></div>
  </div>
</section>

<section class="story-section" aria-labelledby="reach-title">
  <div class="section-head">
    <div><div class="section-kicker">01 · Network reach</div><h2 id="reach-title">A bigger network does not always reach more countries.</h2></div>
    <p class="takeaway"><strong>Takeaway.</strong> FR lists far more directed routes, while TK and AF span much broader country portfolios in this historical snapshot.</p>
  </div>
  <div class="reach-comparison" aria-label="Flagship airline reach comparison">
    ${data.flagships.reach.map((d) => html`<div><strong>${d.airline_name}</strong><span>${number(d.directed_route_presences)} routes / ${number(d.distinct_country_count)} countries</span></div>`)}
  </div>
  <div class="chart-wrap">${resize((width) => reachChart(data, selectedAirlineKey, {width}))}</div>
  <div class="selected-strip">
    <div><span class="descriptor">Selected airline</span><span class="selected-name">${selectedAirline.airline_name} (${selectedAirline.airline_code})</span></div>
    <div><span class="descriptor">Route presences</span><span class="metric">${number(selectedAirline.directed_route_presences)}</span></div>
    <div><span class="descriptor">Countries reached</span><span class="metric">${number(selectedAirline.distinct_country_count)}</span></div>
    <div><span class="descriptor">P90 route distance</span><span class="metric">${number(Math.round(selectedAirline.p90_route_distance_km))} km</span></div>
  </div>
</section>

<section class="story-section" aria-labelledby="hub-title">
  <div class="section-head">
    <div><div class="section-kicker">02 · Hub structure</div><h2 id="hub-title">Same network size. Very different dependence on origin hubs.</h2></div>
    <p class="takeaway"><strong>Takeaway.</strong> Route count does not mechanically determine origin concentration; effective hubs summarizes how evenly route presences are distributed across origins.</p>
  </div>
  <div class="hub-comparison" aria-label="Same-size airline hub comparison">
    ${data.flagships.hubs.map((d) => html`<div><strong>${d.airline_name}</strong><span class="comparison-route">${number(d.directed_route_presences)} routes</span><span class="comparison-value">${d.effective_hubs.toFixed(2)}</span><span class="comparison-label">effective hubs</span></div>`)}
  </div>
  <div class="chart-wrap">${resize((width) => hubChart(data, selectedAirlineKey, {width}))}</div>
</section>

<section class="story-section" aria-labelledby="codeshare-title">
  <div class="section-head">
    <div><div class="section-kicker">03 · Codeshare sensitivity</div><h2 id="codeshare-title">Codeshare-associated reach is material for a subset—not universal.</h2></div>
    <p class="takeaway"><strong>Takeaway.</strong> Including listed codeshare records expands apparent reach for 146 airlines, while 420 show no route-presence uplift.</p>
  </div>
  <div class="uplift-summary">
    <div><strong>${number(data.meta.positive_codeshare_uplift_airlines)}</strong><span>airlines with positive route uplift</span></div>
    <div><strong>${number(data.meta.zero_codeshare_uplift_airlines)}</strong><span>airlines with zero route uplift</span></div>
    <div><strong>${percent(data.meta.top_five_codeshare_uplift_share, 2)}</strong><span>of total uplift concentrated in the top five airlines</span></div>
  </div>
  <div class="chart-wrap">${resize((width) => codeshareChart(data, selectedAirlineKey, {width}))}</div>
  ${selectedCodeshare ? html`<div class="selected-strip">
    <div><span class="descriptor">Selected airline</span><span class="selected-name">${selectedCodeshare.airline_name ?? selectedCodeshare.airline_code} (${selectedCodeshare.airline_code})</span></div>
    <div><span class="descriptor">Route uplift</span><span class="metric">+${number(selectedCodeshare.route_presence_uplift)}</span></div>
    <div><span class="descriptor">Airport uplift</span><span class="metric">+${number(selectedCodeshare.airport_coverage_uplift)}</span></div>
    <div><span class="descriptor">Country uplift</span><span class="metric">+${number(selectedCodeshare.country_coverage_uplift)}</span></div>
  </div>` : null}
</section>

<section class="support-section" aria-labelledby="support-title">
  <div class="section-kicker">Decision support</div>
  <h2 id="support-title">What this analysis supports</h2>
  <ul>
    <li>Comparing network breadth with geographic reach</li>
    <li>Screening dependence on a small number of origin hubs</li>
    <li>Assessing how codeshare listings change apparent network coverage</li>
  </ul>
</section>

<section class="story-section" id="methodology" aria-labelledby="method-title">
  <div class="section-head">
    <div><div class="section-kicker">04 · Methodology & data quality</div><h2 id="method-title">Built to make the limits visible.</h2></div>
    <p class="takeaway"><strong>Takeaway.</strong> Structural route presence supports network screening and benchmarking; frequency, capacity, traffic, revenue and current schedules require other data.</p>
  </div>
  <div class="method-grid">
    <div><h3>Historical, not current</h3><p>OpenFlights 2014 is treated as a fixed historical snapshot. Inactive airlines are retained, and no claim is made about present-day strategy or operations.</p></div>
    <div><h3>Primary comparison</h3><p>Airline comparisons use non-codeshare route presences and default to at least 50 records. All joins use the stable <code>airline_key</code>.</p></div>
    <div><h3>Verified geography</h3><p>Country, international-share and distance fields come from <code>airline_geographic_reach</code>. Unique-code resolutions are included and conflicts remain quality-flagged.</p></div>
  </div>
  <div class="quality-line"><strong>${number(data.meta.geographic_route_presences)} geographic route presences retained</strong> <span>· ${number(data.meta.geographic_excluded_route_presences)} primary records excluded · airport ID 5613 regression count: ${number(data.meta.airport_5613_geographic_eligible_rows)}</span></div>
</section>

<footer class="page-footer">
  <p>Designed and built end-to-end by Di Lu using Python, SQL, Observable Framework and reproducible data-quality checks.</p>
  <div><span>Airline Network Structure &amp; Connectivity Analytics</span><span>OpenFlights 2014 · historical directed route presence · no frequency or traffic inference</span></div>
</footer>
