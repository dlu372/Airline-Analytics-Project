# Airline-Analytics-Project
End-to-end airline data analytics project using SQL, Python and Power BI.  Exploring airline route performance, seasonality impact and route optimization insights.

## Project Overview
This project explores how airline route networks are structured — 
specifically, whether airlines tend to concentrate traffic on a small number of core routes 
or distribute capacity more evenly across their networks.

Using OpenFlights route data, the analysis applies network concentration metrics 
(such as Top-N route share and HHI) to compare structural differences across airlines.
The project demonstrates how simplified concentration proxies can effectively capture 
complex network behaviors.

# ✈️ Airline Network Analytics (SQL • Python • Power BI)

**End-to-end analytics project** that builds an analysis-ready airline route dataset and delivers **network strategy insights** through **SQL-based metrics** and an **interactive Power BI dashboard**.

> Core question: **Are airline route networks concentrated on a few routes, or distributed across many?**  
> Key metrics: **Top-10 route share** + **HHI (Herfindahl–Hirschman Index)**

---

## 🔥 Why this project matters (Business Value)

Airline network structure is a strategic asset. Understanding **route portfolio concentration** helps decision-makers:

- **Network planning**: hub-and-spoke vs. distributed strategies; expansion priorities  
- **Risk management**: dependence on “trunk” routes and single points of failure  
- **Resilience & competition**: monopoly exposure on certain airport-route segments  
- **Operational complexity**: fleet/equipment diversity as a proxy for operational variety

This project is designed to demonstrate not only dashboarding, but **analytical thinking + metric design + reproducible workflow**.

---

## 🧠 What I built (Deliverables)

### 1) Analysis-ready dataset (Python)
- Cleaned OpenFlights raw `.dat` files (airports / airlines / routes)
- Standardized schema & missing values (`\N` → `NA`)
- Resolved join-key type issues (string casting for airport IDs)
- Enriched routes by joining:
  - source airport metadata (IATA, country, lat/long)
  - destination airport metadata (IATA, country, lat/long)
- Output:
  - `data/processed/routes_enriched.csv` (imported into SQLite for analysis)

### 2) Deep SQL analytics (SQLite)
Built reusable views and advanced metrics to answer network questions:
- **Airport Hub Index** (departures, unique destinations, frequency intensity)
- **Strong bidirectional connections** (top airport pairs)
- **International exposure** (% cross-country routes)
- **Monopoly exposure risk** (routes served by only one airline)
- **Airline breadth vs. focus** (origins/destinations/country coverage)
- **Equipment diversity proxy** (fleet complexity indicator)

**Flagship analysis: Network concentration**
- Route frequency table per airline-route
- **Top-10 route share** (% of traffic represented by the 10 most frequent routes)
- **HHI** from route-level shares: `HHI = Σ share²`
- Segmentation into three groups (distributed vs. moderate vs. high concentration)
  - Implemented using **relative thresholds / percentile logic** (more appropriate for network HHI scale)

Outputs exported for BI:
- `data/processed/airline_network_concentration.csv`

### 3) Power BI interactive dashboard
Key visuals built:
- **Bar**: Count of airlines by concentration label  
- **Table**: airline-level metrics (`top10_share_pct`, `hhi`, `total_route_count`, label)  
- **Scatter (core)**: `Top-10 share` (X) × `HHI` (Y), bubble size = `route count`, color = `concentration_label`  
- **Slicer**: filter by concentration label for interactive exploration  
- (Optional) reference lines/quadrant logic for “network structure” storytelling

---

## 📊 Key Metrics (Explainable to HR & stakeholders)

### Top-10 Route Share
Measures how dependent an airline is on its **top 10 most frequent routes**.

- Higher → network depends heavily on a small set of routes  
- Lower → traffic is spread more evenly

### HHI (Herfindahl–Hirschman Index)
A standard concentration metric (often used in economics / competition analysis), adapted here for **route portfolio concentration**.

- HHI close to 0 → highly distributed route portfolio  
- Higher HHI → more concentrated portfolio

> Note: For airline route networks, HHI values are naturally small (many routes).  
> Therefore, **relative segmentation (percentile/within-sample thresholds)** is more meaningful than classic market HHI cutoffs.

---

## 🗂 Repository Structure

```text
Airline-Analytics-Project/
├── data/
│   ├── raw/                         # OpenFlights raw files (.dat)
│   └── processed/                   # cleaned & analysis-ready outputs
│       ├── airports_clean.csv
│       ├── airlines_clean.csv
│       ├── routes_clean.csv
│       ├── routes_enriched.csv
│       └── airline_network_concentration.csv
├── Python/
│   └── load_openflights_data.py     # data cleaning + enrichment pipeline (Pandas)
├── sql/
│   ├── basic_analysis.sql           # hub / intl / monopoly / breadth / equipment proxy
│   └── advanced_analysis.sql        # Top10 share + HHI + concentration segmentation
├── powerbi/
│   └── (dashboard.pbix)             # optional: local PBIX
├── Report/
│   └── (screenshots / write-up)     # optional: exported visuals & narrative
├── README.md
└── .gitignore