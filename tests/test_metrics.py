import sqlite3
import unittest
from pathlib import Path

import pandas as pd

from src.config import ANALYTICS_DIR, ANALYTICS_TABLES, DATABASE_PATH, PROJECT_ROOT
from src.metrics import calculate_hub_values, haversine_km, reciprocal_route_share
from src.loaders import load_raw_tables
from src.resolution import resolve_route_endpoints


class MetricDefinitionTests(unittest.TestCase):
    def test_haversine_one_degree_at_equator(self) -> None:
        distance = haversine_km([0.0], [0.0], [0.0], [1.0])[0]
        self.assertAlmostEqual(distance, 111.195, places=3)

    def test_hub_dependence_uses_origin_distribution(self) -> None:
        frame = pd.DataFrame({"source_airport_id": [1, 1, 1, 2]})
        values = calculate_hub_values(frame)
        self.assertAlmostEqual(values["top1_origin_share"], 0.75)
        self.assertAlmostEqual(values["top3_origin_share"], 1.0)
        self.assertAlmostEqual(values["origin_airport_hhi"], 0.625)
        self.assertAlmostEqual(values["effective_hubs"], 1.6)
        self.assertEqual(values["distinct_origin_airports"], 2)

    def test_reciprocal_route_share(self) -> None:
        frame = pd.DataFrame(
            {
                "source_airport_id": [1, 2, 1],
                "destination_airport_id": [2, 1, 3],
            }
        )
        self.assertAlmostEqual(reciprocal_route_share(frame), 2.0 / 3.0)


class GeneratedOutputTests(unittest.TestCase):
    def test_all_contract_tables_exist_without_legacy_metrics(self) -> None:
        forbidden = {
            "top10_share_pct",
            "concentration_label",
            "total_route_count",
        }
        for table in ANALYTICS_TABLES:
            path = ANALYTICS_DIR / f"{table}.csv"
            self.assertTrue(path.exists(), path)
            columns = set(pd.read_csv(path, nrows=0).columns)
            self.assertTrue(forbidden.isdisjoint(columns), (table, columns))

    def test_database_contains_contract_tables(self) -> None:
        self.assertTrue(DATABASE_PATH.exists())
        connection = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(set(ANALYTICS_TABLES).issubset(tables))
            self.assertEqual(
                connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
            )
        finally:
            connection.close()

    def test_raw_files_are_unchanged(self) -> None:
        expected = {
            "airlines.dat": "39be1a432e8b04ebc12860c29281c974a9cb52169c82b2456a835d66ab1548a1",
            "airports.dat": "9387cdb38df5bd664da823f8ccb69fdd9b33a1888f5b7cca09c34a3cd9ff59f9",
            "routes.dat": "bd373706238134f619c624c606dccc74c05c2582a977c489c81de501735f2390",
        }
        import hashlib

        for filename, checksum in expected.items():
            data = (PROJECT_ROOT / "data" / "raw" / filename).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), checksum)

    def test_stable_airline_dimension(self) -> None:
        dimension = pd.read_csv(ANALYTICS_DIR / "dim_airline.csv", dtype=str)
        self.assertEqual(len(dimension), 566)
        self.assertFalse(dimension["airline_key"].duplicated().any())
        fallback = dimension[dimension["airline_id"].isna()]
        self.assertEqual(len(fallback), 20)
        self.assertTrue(fallback["airline_key"].str.startswith("code:").all())

    def test_airline_origin_detail_primary_key(self) -> None:
        detail = pd.read_csv(ANALYTICS_DIR / "airline_origin_detail.csv", dtype=str)
        self.assertFalse(
            detail.duplicated(["airline_key", "origin_airport_key"]).any()
        )
        shares = pd.to_numeric(detail["origin_route_share"]).groupby(
            detail["airline_key"]
        ).sum()
        self.assertTrue((shares.sub(1.0).abs() < 1e-9).all())

    def test_affected_geographic_outputs_are_consistent(self) -> None:
        geographic = pd.read_csv(ANALYTICS_DIR / "airline_geographic_reach.csv")
        summary = pd.read_csv(ANALYTICS_DIR / "airline_network_summary.csv")
        joined = geographic.merge(
            summary[["airline_key", "directed_route_presences"]],
            on="airline_key",
            validate="one_to_one",
        )
        accounted = (
            joined["valid_distance_route_presences"]
            + joined["invalid_or_missing_distance_route_presences"]
        )
        self.assertTrue(accounted.eq(joined["directed_route_presences"]).all())

        connectivity = pd.read_csv(ANALYTICS_DIR / "airport_connectivity.csv")
        self.assertFalse(connectivity["airport_id"].eq(5613).any())
        self.assertFalse(connectivity["airport_key"].duplicated().any())

        diversity = pd.read_csv(ANALYTICS_DIR / "route_carrier_diversity.csv")
        self.assertFalse(
            diversity.duplicated(
                ["source_airport_id", "destination_airport_id"]
            ).any()
        )
        excluded = ~diversity["geographic_metric_eligible"]
        self.assertTrue(diversity.loc[excluded, "source_airport_name"].isna().all())

    def test_airport_5613_is_not_geography_eligible(self) -> None:
        airports, _, routes = load_raw_tables(PROJECT_ROOT / "data" / "raw")
        affected = routes.loc[
            routes["source_airport_id"].eq(5613)
            | routes["destination_airport_id"].eq(5613)
        ]
        resolved, _ = resolve_route_endpoints(affected, airports)
        self.assertEqual(len(resolved), 4)
        self.assertFalse(resolved["geographic_metric_eligible"].any())
        statuses = set(resolved["source_resolution_status"]) | set(
            resolved["destination_resolution_status"]
        )
        self.assertIn("id_only", statuses)


if __name__ == "__main__":
    unittest.main()
