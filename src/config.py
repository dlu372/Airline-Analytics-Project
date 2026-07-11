from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
CHECKSUM_MANIFEST = RAW_DIR / "checksums.sha256"
DATABASE_PATH = ANALYTICS_DIR / "airline_network_analytics.sqlite"

EXPECTED_ROUTE_ROWS = 67_663

AIRPORT_COLUMNS = [
    "airport_id",
    "name",
    "city",
    "country",
    "iata",
    "icao",
    "latitude",
    "longitude",
    "altitude",
    "timezone",
    "dst",
    "tz_database_time_zone",
    "type",
    "source",
]

AIRLINE_COLUMNS = [
    "airline_id",
    "name",
    "alias",
    "iata",
    "icao",
    "callsign",
    "country",
    "active",
]

ROUTE_COLUMNS = [
    "airline_code",
    "airline_id",
    "source_airport",
    "source_airport_id",
    "destination_airport",
    "destination_airport_id",
    "codeshare",
    "stops",
    "equipment",
]

PROCESSED_OUTPUTS = [
    "airports_clean.csv",
    "airlines_clean.csv",
    "routes_clean.csv",
    "routes_enriched.csv",
]

ANALYTICS_TABLES = [
    "dim_airline",
    "airline_network_summary",
    "airline_hub_dependence",
    "airline_geographic_reach",
    "airport_connectivity",
    "route_carrier_diversity",
    "codeshare_sensitivity",
    "airline_origin_detail",
]
