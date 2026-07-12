"""Read-only validation of Phase 2 analytics outputs.

Run from the repository root:

    python analysis/validate_outputs.py

The script prints evidence to stdout and does not modify project files.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.metrics import haversine_km  # noqa: E402

ANALYTICS = ROOT / "data" / "analytics"
DATABASE = ANALYTICS / "airline_network_analytics.sqlite"


def airline_key(frame: pd.DataFrame) -> pd.Series:
    ids = pd.to_numeric(frame["airline_id"], errors="coerce").astype("Int64")
    return ids.astype("string").fillna("code:" + frame["airline_code"].fillna("UNKNOWN"))


def load_outputs() -> dict[str, pd.DataFrame]:
    names = [
        "airline_network_summary",
        "airline_hub_dependence",
        "airline_geographic_reach",
        "airport_connectivity",
        "route_carrier_diversity",
        "codeshare_sensitivity",
    ]
    outputs = {name: pd.read_csv(ANALYTICS / f"{name}.csv") for name in names}
    for name in [
        "airline_network_summary",
        "airline_hub_dependence",
        "airline_geographic_reach",
        "codeshare_sensitivity",
    ]:
        outputs[name]["_airline_key"] = airline_key(outputs[name])
    return outputs


def describe_series(series: pd.Series) -> dict[str, float | int]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return {
        "n": int(len(values)),
        "min": float(values.min()),
        "median": float(values.median()),
        "mean": float(values.mean()),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }


def spearman_correlation(left: pd.Series, right: pd.Series) -> float:
    """Spearman correlation without requiring SciPy."""
    return float(left.rank(method="average").corr(right.rank(method="average")))


def print_frame(title: str, frame: pd.DataFrame) -> None:
    print(f"\n## {title}")
    print(frame.to_string(index=False))


def consistency_audit(outputs: dict[str, pd.DataFrame]) -> None:
    print("\n# CONSISTENCY")
    key_contracts = {
        "airline_network_summary": ["_airline_key"],
        "airline_hub_dependence": ["_airline_key"],
        "airline_geographic_reach": ["_airline_key"],
        "codeshare_sensitivity": ["_airline_key"],
        "airport_connectivity": ["airport_id"],
        "route_carrier_diversity": [
            "source_airport_id",
            "destination_airport_id",
        ],
    }
    rows = []
    for name, frame in outputs.items():
        keys = key_contracts[name]
        rows.append(
            {
                "table": name,
                "rows": len(frame),
                "columns": len(frame.columns) - int("_airline_key" in frame.columns),
                "duplicate_keys": int(frame.duplicated(keys).sum()),
                "missing_key_values": int(frame[keys].isna().any(axis=1).sum()),
                "missing_airline_id": int(frame["airline_id"].isna().sum())
                if "airline_id" in frame
                else 0,
                "missing_airline_code": int(frame["airline_code"].isna().sum())
                if "airline_code" in frame
                else 0,
                "missing_airline_name": int(frame["airline_name"].isna().sum())
                if "airline_name" in frame
                else 0,
            }
        )
    print_frame("Table contracts", pd.DataFrame(rows))

    summary_keys = set(outputs["airline_network_summary"]["_airline_key"])
    hub_keys = set(outputs["airline_hub_dependence"]["_airline_key"])
    geo_keys = set(outputs["airline_geographic_reach"]["_airline_key"])
    sensitivity_keys = set(outputs["codeshare_sensitivity"]["_airline_key"])
    print("summary=hub", summary_keys == hub_keys)
    print("summary=geographic", summary_keys == geo_keys)
    print("sensitivity extra keys", sorted(sensitivity_keys - summary_keys))
    print("summary missing from sensitivity", sorted(summary_keys - sensitivity_keys))
    extra = outputs["codeshare_sensitivity"].loc[
        outputs["codeshare_sensitivity"]["_airline_key"].isin(
            sensitivity_keys - summary_keys
        )
    ]
    print_frame(
        "Codeshare-only airlines",
        extra[
            [
                "_airline_key",
                "airline_id",
                "airline_code",
                "airline_name",
                "non_codeshare_route_presence_count",
                "all_listed_route_presence_count",
            ]
        ],
    )

    summary = outputs["airline_network_summary"]
    duplicate_names = (
        summary.dropna(subset=["airline_name"])
        .groupby("airline_name")
        .agg(keys=("_airline_key", "nunique"), codes=("airline_code", lambda x: ";".join(sorted(set(x.dropna())))))
        .query("keys > 1")
        .reset_index()
    )
    print_frame("Duplicate airline names across keys", duplicate_names)
    print("airline_active counts", summary["airline_active"].fillna("<missing>").value_counts().to_dict())
    diversity = outputs["route_carrier_diversity"]
    print(
        "route diversity rows with missing source/destination IATA",
        int((diversity["source_iata"].isna() | diversity["destination_iata"].isna()).sum()),
    )

    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    routes = pd.read_sql_query(
        "SELECT airline_code, source_airport, source_airport_id, "
        "destination_airport, destination_airport_id FROM routes_enriched",
        connection,
    )
    airports = pd.read_sql_query(
        "SELECT airport_id, iata, icao, name, country FROM airports_clean",
        connection,
    )
    connection.close()
    source_lookup = airports.add_prefix("source_dim_")
    destination_lookup = airports.add_prefix("destination_dim_")
    checked = routes.merge(
        source_lookup,
        left_on="source_airport_id",
        right_on="source_dim_airport_id",
        how="left",
    ).merge(
        destination_lookup,
        left_on="destination_airport_id",
        right_on="destination_dim_airport_id",
        how="left",
    )
    source_matches = checked["source_airport"].eq(checked["source_dim_iata"]) | checked[
        "source_airport"
    ].eq(checked["source_dim_icao"])
    destination_matches = checked["destination_airport"].eq(
        checked["destination_dim_iata"]
    ) | checked["destination_airport"].eq(checked["destination_dim_icao"])
    source_dimension_missing = checked["source_dim_airport_id"].isna()
    destination_dimension_missing = checked["destination_dim_airport_id"].isna()
    source_code_mismatch = ~source_dimension_missing & ~source_matches.fillna(False)
    destination_code_mismatch = ~destination_dimension_missing & ~destination_matches.fillna(False)
    mismatch = checked.loc[source_code_mismatch | destination_code_mismatch]
    print("source airport dimension missing rows", int(source_dimension_missing.sum()))
    print("destination airport dimension missing rows", int(destination_dimension_missing.sum()))
    print("source code mismatch on matched airport ID rows", int(source_code_mismatch.sum()))
    print("destination code mismatch on matched airport ID rows", int(destination_code_mismatch.sum()))
    print("either endpoint code mismatch on matched airport ID rows", len(mismatch))
    print_frame(
        "Matched airport IDs with route-code/dimension-code mismatch examples",
        mismatch[[
            "airline_code", "source_airport", "source_airport_id", "source_dim_iata",
            "source_dim_icao", "source_dim_name", "destination_airport",
            "destination_airport_id", "destination_dim_iata", "destination_dim_icao",
            "destination_dim_name",
        ]].head(20),
    )


def independent_recalculation(outputs: dict[str, pd.DataFrame]) -> None:
    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    routes = pd.read_sql_query("SELECT * FROM route_presences_non_codeshare", connection)
    connection.close()
    summary = outputs["airline_network_summary"].set_index("airline_code")
    hub = outputs["airline_hub_dependence"].set_index("airline_code")
    geo = outputs["airline_geographic_reach"].set_index("airline_code")

    complete = outputs["airline_network_summary"].dropna(subset=["airline_name"])
    large = complete.nlargest(3, "directed_route_presences")
    regional = complete.loc[
        complete["airline_code"].isin(["ZL", "9K", "8E"])
    ].sort_values("directed_route_presences", ascending=False, kind="stable")
    stable = complete.loc[complete["directed_route_presences"] >= 50]
    stable_hub = stable.merge(
        outputs["airline_hub_dependence"][
            ["_airline_key", "origin_airport_hhi", "top1_origin_share"]
        ],
        on="_airline_key",
    )
    high_hub = stable_hub.nlargest(3, "origin_airport_hhi")
    low_hub = stable_hub.nsmallest(3, "origin_airport_hhi")

    print_frame(
        "Large network sample",
        large[
            [
                "airline_code",
                "airline_name",
                "directed_route_presences",
                "distinct_airports",
                "distinct_countries",
            ]
        ],
    )
    print_frame(
        "Historical regional-airline sample",
        regional[
            [
                "airline_code",
                "airline_name",
                "directed_route_presences",
                "distinct_airports",
                "distinct_countries",
            ]
        ],
    )
    print_frame(
        "High hub dependence sample (>=50 routes)",
        high_hub[
            [
                "airline_code",
                "airline_name",
                "directed_route_presences",
                "top1_origin_share",
                "origin_airport_hhi",
            ]
        ],
    )
    print_frame(
        "Low hub dependence sample (>=50 routes)",
        low_hub[
            [
                "airline_code",
                "airline_name",
                "directed_route_presences",
                "top1_origin_share",
                "origin_airport_hhi",
            ]
        ],
    )

    codes = sorted(
        set(large["airline_code"])
        | set(regional["airline_code"])
        | set(high_hub["airline_code"])
        | set(low_hub["airline_code"])
    )
    validations = []
    for code in codes:
        group = routes.loc[routes["airline_code"] == code].copy()
        edges = set(
            zip(group["source_airport_id"].astype(int), group["destination_airport_id"].astype(int))
        )
        reciprocal = sum((d, s) in edges for s, d in edges) / len(edges)
        origin_counts = group.groupby("source_airport_id").size()
        origin_shares = origin_counts / origin_counts.sum()
        distance = haversine_km(
            group["source_latitude"],
            group["source_longitude"],
            group["destination_latitude"],
            group["destination_longitude"],
        )
        recalculated = {
            "directed_route_presences": len(group),
            "distinct_origin_airports": group["source_airport_id"].nunique(),
            "distinct_destination_airports": group["destination_airport_id"].nunique(),
            "international_route_presence_share": (
                group["source_country"].ne(group["destination_country"]).mean()
            ),
            "reciprocal_route_share": reciprocal,
            "top1_origin_share": origin_shares.max(),
            "top3_origin_share": origin_shares.nlargest(3).sum(),
            "origin_airport_hhi": np.square(origin_shares).sum(),
            "effective_hubs": 1.0 / np.square(origin_shares).sum(),
            "median_route_distance_km": np.median(distance),
            "p90_route_distance_km": np.percentile(distance, 90),
        }
        stored = {
            "directed_route_presences": summary.loc[code, "directed_route_presences"],
            "distinct_origin_airports": summary.loc[code, "distinct_origin_airports"],
            "distinct_destination_airports": summary.loc[code, "distinct_destination_airports"],
            "international_route_presence_share": summary.loc[code, "international_route_presence_share"],
            "reciprocal_route_share": summary.loc[code, "reciprocal_route_share"],
            "top1_origin_share": hub.loc[code, "top1_origin_share"],
            "top3_origin_share": hub.loc[code, "top3_origin_share"],
            "origin_airport_hhi": hub.loc[code, "origin_airport_hhi"],
            "effective_hubs": hub.loc[code, "effective_hubs"],
            "median_route_distance_km": geo.loc[code, "median_route_distance_km"],
            "p90_route_distance_km": geo.loc[code, "p90_route_distance_km"],
        }
        differences = {
            metric: abs(float(recalculated[metric]) - float(stored[metric]))
            for metric in recalculated
        }
        validations.append(
            {
                "airline_code": code,
                "routes": len(group),
                "max_abs_difference": max(differences.values()),
            }
        )
    print_frame("Independent recalculation results", pd.DataFrame(validations))

    airports = outputs["airport_connectivity"].nlargest(
        3, "outgoing_distinct_destinations"
    )
    print_frame(
        "High-connectivity airports",
        airports[
            [
                "airport_id",
                "airport_iata",
                "airport_name",
                "outgoing_distinct_destinations",
                "incoming_distinct_origins",
                "outgoing_listed_airlines",
                "reciprocal_connectivity_ratio",
            ]
        ],
    )
    diversity = outputs["route_carrier_diversity"].nlargest(
        3, "listed_carrier_count"
    )
    print_frame(
        "High carrier-diversity directed ODs",
        diversity[
            [
                "source_airport_id",
                "source_iata",
                "destination_airport_id",
                "destination_iata",
                "listed_carrier_count",
                "listed_carrier_names",
            ]
        ],
    )


def distribution_and_threshold_audit(outputs: dict[str, pd.DataFrame]) -> None:
    metric_map = {
        "airline_network_summary": [
            "directed_route_presences",
            "distinct_origin_airports",
            "distinct_destination_airports",
            "distinct_airports",
            "distinct_countries",
            "international_route_presence_share",
            "reciprocal_route_share",
            "codeshare_route_presence_share",
        ],
        "airline_hub_dependence": [
            "top1_origin_share",
            "top3_origin_share",
            "origin_airport_hhi",
            "effective_hubs",
        ],
        "airline_geographic_reach": [
            "mean_route_distance_km",
            "median_route_distance_km",
            "p90_route_distance_km",
        ],
        "airport_connectivity": [
            "outgoing_distinct_destinations",
            "incoming_distinct_origins",
            "outgoing_listed_airlines",
            "incoming_listed_airlines",
            "international_destination_count",
            "reciprocal_connectivity_ratio",
        ],
        "route_carrier_diversity": ["listed_carrier_count"],
        "codeshare_sensitivity": [
            "route_presence_uplift",
            "airport_coverage_uplift",
            "country_coverage_uplift",
            "top1_origin_share_difference",
            "origin_hhi_difference",
            "effective_hubs_difference",
        ],
    }
    rows = []
    for table, metrics in metric_map.items():
        for metric in metrics:
            rows.append(
                {"table": table, "metric": metric, **describe_series(outputs[table][metric])}
            )
    print_frame("Metric distributions", pd.DataFrame(rows))

    summary = outputs["airline_network_summary"]
    hub = outputs["airline_hub_dependence"][
        ["_airline_key", "top1_origin_share", "origin_airport_hhi", "effective_hubs"]
    ]
    joined = summary.merge(hub, on="_airline_key")
    total_routes = joined["directed_route_presences"].sum()
    threshold_rows = []
    for threshold in [20, 50, 100]:
        sample = joined.loc[joined["directed_route_presences"] >= threshold]
        threshold_rows.append(
            {
                "threshold": threshold,
                "airlines": len(sample),
                "airline_coverage_share": len(sample) / len(joined),
                "route_presence_coverage_share": sample[
                    "directed_route_presences"
                ].sum()
                / total_routes,
                "median_top1_origin_share": sample["top1_origin_share"].median(),
                "median_origin_hhi": sample["origin_airport_hhi"].median(),
                "median_effective_hubs": sample["effective_hubs"].median(),
                "single_route_change_max_share_pp": 100.0 / threshold,
            }
        )
    print_frame("Threshold sensitivity", pd.DataFrame(threshold_rows))

    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    routes = pd.read_sql_query(
        "SELECT airline_code, source_airport_id, source_iata, destination_airport_id, "
        "destination_iata, source_airport_name, destination_airport_name, "
        "source_latitude, source_longitude, destination_latitude, destination_longitude "
        "FROM route_presences_non_codeshare",
        connection,
    )
    connection.close()
    routes["distance_km"] = haversine_km(
        routes["source_latitude"],
        routes["source_longitude"],
        routes["destination_latitude"],
        routes["destination_longitude"],
    )
    print_frame(
        "Longest route-presence distances",
        routes.nlargest(10, "distance_km")[[
            "airline_code",
            "source_airport_id",
            "source_iata",
            "source_airport_name",
            "destination_airport_id",
            "destination_iata",
            "destination_airport_name",
            "distance_km",
        ]],
    )

    sensitivity = outputs["codeshare_sensitivity"].copy()
    total_uplift = sensitivity["route_presence_uplift"].sum()
    top = sensitivity.nlargest(10, "route_presence_uplift").copy()
    top["uplift_share"] = top["route_presence_uplift"] / total_uplift
    print("total codeshare-associated route uplift", int(total_uplift))
    print("top1 uplift share", float(top.iloc[0]["uplift_share"]))
    print("top5 uplift share", float(top.head(5)["uplift_share"].sum()))
    print_frame(
        "Largest codeshare-associated uplifts",
        top[
            [
                "airline_code",
                "airline_name",
                "non_codeshare_route_presence_count",
                "all_listed_route_presence_count",
                "route_presence_uplift",
                "airport_coverage_uplift",
                "country_coverage_uplift",
                "uplift_share",
            ]
        ],
    )


def correlation_audit(outputs: dict[str, pd.DataFrame]) -> None:
    summary = outputs["airline_network_summary"]
    airline = summary.merge(
        outputs["airline_hub_dependence"].drop(
            columns=[
                "airline_id",
                "airline_code",
                "airline_name",
                "airline_country",
                "airline_active",
                "distinct_origin_airports",
            ]
        ),
        on="_airline_key",
    ).merge(
        outputs["airline_geographic_reach"].drop(
            columns=[
                "airline_id",
                "airline_code",
                "airline_name",
                "airline_country",
                "airline_active",
                "domestic_route_presence_share",
                "international_route_presence_share",
            ]
        ),
        on="_airline_key",
    )
    sensitivity = outputs["codeshare_sensitivity"]
    airline = airline.merge(
        sensitivity[["_airline_key", "route_presence_uplift"]],
        on="_airline_key",
        how="left",
    )

    pairs = [
        ("network breadth vs top1", "directed_route_presences", "top1_origin_share"),
        ("network breadth vs origin HHI", "directed_route_presences", "origin_airport_hhi"),
        ("route count vs effective hubs", "directed_route_presences", "effective_hubs"),
        ("international share vs median distance", "international_route_presence_share", "median_route_distance_km"),
        ("international share vs P90 distance", "international_route_presence_share", "p90_route_distance_km"),
        ("country coverage vs median distance", "distinct_countries", "median_route_distance_km"),
        ("country coverage vs P90 distance", "distinct_countries", "p90_route_distance_km"),
        ("codeshare uplift vs non-codeshare breadth", "route_presence_uplift", "directed_route_presences"),
        ("top1 share vs origin HHI", "top1_origin_share", "origin_airport_hhi"),
        ("effective hubs vs distinct origins", "effective_hubs", "distinct_origin_airports"),
    ]
    rows = []
    for scope, sample in [
        ("all", airline),
        (">=50 routes", airline.loc[airline["directed_route_presences"] >= 50]),
        (">=100 routes", airline.loc[airline["directed_route_presences"] >= 100]),
    ]:
        for label, left, right in pairs:
            values = sample[[left, right]].dropna()
            rows.append(
                {
                    "scope": scope,
                    "relationship": label,
                    "n": len(values),
                    "pearson": values[left].corr(values[right], method="pearson"),
                    "spearman": spearman_correlation(values[left], values[right]),
                }
            )

    airport = outputs["airport_connectivity"].copy()
    diversity = outputs["route_carrier_diversity"]
    choice = (
        diversity.groupby("source_airport_id")["listed_carrier_count"]
        .mean()
        .rename("mean_listed_carriers_per_outgoing_od")
    )
    airport = airport.merge(choice, left_on="airport_id", right_index=True, how="left")
    values = airport[
        ["outgoing_distinct_destinations", "mean_listed_carriers_per_outgoing_od"]
    ].dropna()
    rows.append(
        {
            "scope": "airports",
            "relationship": "airport connectivity vs mean carrier choice",
            "n": len(values),
            "pearson": values.iloc[:, 0].corr(values.iloc[:, 1], method="pearson"),
            "spearman": spearman_correlation(values.iloc[:, 0], values.iloc[:, 1]),
        }
    )
    print_frame("Correlations", pd.DataFrame(rows))

    varying = (
        airline.groupby("directed_route_presences")["origin_airport_hhi"]
        .agg(["count", "nunique", "min", "max"])
        .query("count >= 3 and nunique > 1")
        .assign(range=lambda x: x["max"] - x["min"])
        .sort_values("range", ascending=False)
        .head(10)
        .reset_index()
    )
    print_frame("Same-size airlines with different origin HHI", varying)


def main() -> None:
    outputs = load_outputs()
    consistency_audit(outputs)
    independent_recalculation(outputs)
    distribution_and_threshold_audit(outputs)
    correlation_audit(outputs)


if __name__ == "__main__":
    main()
