from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


AIRLINE_METADATA_COLUMNS = [
    "airline_key",
    "airline_id",
    "airline_code",
    "airline_name",
    "airline_country",
    "airline_active",
]


def _comparison_flags(route_presence_count: int) -> dict[str, bool]:
    return {
        "comparison_threshold_20": route_presence_count >= 20,
        "comparison_threshold_50": route_presence_count >= 50,
        "comparison_threshold_100": route_presence_count >= 100,
        "dashboard_default_eligible": route_presence_count >= 50,
    }


def _first_value(frame: pd.DataFrame, column: str) -> Any:
    values = frame[column].dropna()
    return values.iloc[0] if not values.empty else pd.NA


def _airline_metadata(frame: pd.DataFrame) -> dict[str, Any]:
    return {column: _first_value(frame, column) for column in AIRLINE_METADATA_COLUMNS}


def _known_country_shares(frame: pd.DataFrame) -> tuple[float, float]:
    known = frame.loc[
        frame["source_country"].notna() & frame["destination_country"].notna()
    ]
    if known.empty:
        return np.nan, np.nan
    domestic = known["source_country"].eq(known["destination_country"]).mean()
    return float(domestic), float(1.0 - domestic)


def _distinct_union(left: pd.Series, right: pd.Series) -> int:
    values = pd.concat([left, right], ignore_index=True).dropna().unique()
    return int(len(values))


def calculate_hub_values(frame: pd.DataFrame) -> dict[str, float | int]:
    counts = frame.groupby("source_airport_id", dropna=True).size()
    if counts.empty:
        return {
            "top1_origin_share": np.nan,
            "top3_origin_share": np.nan,
            "origin_airport_hhi": np.nan,
            "effective_hubs": np.nan,
            "distinct_origin_airports": 0,
        }
    shares = counts.astype(float) / counts.sum()
    hhi = float(np.square(shares).sum())
    return {
        "top1_origin_share": float(shares.max()),
        "top3_origin_share": float(shares.nlargest(3).sum()),
        "origin_airport_hhi": hhi,
        "effective_hubs": float(1.0 / hhi),
        "distinct_origin_airports": int(len(shares)),
    }


def reciprocal_route_share(frame: pd.DataFrame) -> float:
    edges = {
        (int(source), int(destination))
        for source, destination in frame[
            ["source_airport_id", "destination_airport_id"]
        ].itertuples(index=False, name=None)
    }
    if not edges:
        return np.nan
    reciprocal = sum((destination, source) in edges for source, destination in edges)
    return reciprocal / len(edges)


def build_airline_network_summary(
    non_codeshare: pd.DataFrame,
    all_listed: pd.DataFrame,
) -> pd.DataFrame:
    all_groups = {key: group for key, group in all_listed.groupby("airline_key")}
    rows: list[dict[str, Any]] = []
    for airline_key, group in non_codeshare.groupby("airline_key"):
        all_group = all_groups.get(airline_key, group)
        domestic_share, international_share = _known_country_shares(group)
        rows.append(
            {
                **_airline_metadata(group),
                **_comparison_flags(len(group)),
                "directed_route_presences": int(len(group)),
                "distinct_origin_airports": int(group["source_airport_id"].nunique()),
                "distinct_destination_airports": int(
                    group["destination_airport_id"].nunique()
                ),
                "distinct_airports": _distinct_union(
                    group["source_airport_id"], group["destination_airport_id"]
                ),
                "distinct_countries": _distinct_union(
                    group["source_country"], group["destination_country"]
                ),
                "domestic_route_presence_share": domestic_share,
                "international_route_presence_share": international_share,
                "reciprocal_route_share": reciprocal_route_share(group),
                "codeshare_route_presence_share": float(
                    all_group["is_codeshare"].mean()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["directed_route_presences", "airline_code"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def build_airline_hub_dependence(non_codeshare: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in non_codeshare.groupby("airline_key"):
        rows.append(
            {
                **_airline_metadata(group),
                **_comparison_flags(len(group)),
                **calculate_hub_values(group),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["origin_airport_hhi", "airline_code"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def haversine_km(
    source_latitude: Iterable[float],
    source_longitude: Iterable[float],
    destination_latitude: Iterable[float],
    destination_longitude: Iterable[float],
) -> np.ndarray:
    source_latitude = np.radians(np.asarray(source_latitude, dtype=float))
    source_longitude = np.radians(np.asarray(source_longitude, dtype=float))
    destination_latitude = np.radians(np.asarray(destination_latitude, dtype=float))
    destination_longitude = np.radians(np.asarray(destination_longitude, dtype=float))
    delta_latitude = destination_latitude - source_latitude
    delta_longitude = destination_longitude - source_longitude
    a = (
        np.sin(delta_latitude / 2.0) ** 2
        + np.cos(source_latitude)
        * np.cos(destination_latitude)
        * np.sin(delta_longitude / 2.0) ** 2
    )
    return 6_371.0088 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


def _valid_coordinate_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["source_latitude"].between(-90, 90)
        & frame["destination_latitude"].between(-90, 90)
        & frame["source_longitude"].between(-180, 180)
        & frame["destination_longitude"].between(-180, 180)
    ).fillna(False)


def build_airline_geographic_reach(non_codeshare: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in non_codeshare.groupby("airline_key"):
        valid_mask = group["geographic_metric_eligible"].fillna(False)
        valid = group.loc[valid_mask]
        if valid.empty:
            mean_distance = median_distance = p90_distance = np.nan
        else:
            distances = haversine_km(
                valid["source_resolved_latitude"],
                valid["source_resolved_longitude"],
                valid["destination_resolved_latitude"],
                valid["destination_resolved_longitude"],
            )
            mean_distance = float(np.mean(distances))
            median_distance = float(np.median(distances))
            p90_distance = float(np.percentile(distances, 90))

        geographic = pd.DataFrame(
            {
                "source_country": valid["source_resolved_country"],
                "destination_country": valid["destination_resolved_country"],
            }
        )
        domestic_share, international_share = _known_country_shares(geographic)
        rows.append(
            {
                **_airline_metadata(group),
                **_comparison_flags(len(group)),
                "mean_route_distance_km": mean_distance,
                "median_route_distance_km": median_distance,
                "p90_route_distance_km": p90_distance,
                "valid_distance_route_presences": int(valid_mask.sum()),
                "invalid_or_missing_distance_route_presences": int(
                    len(group) - valid_mask.sum()
                ),
                "domestic_route_presence_share": domestic_share,
                "international_route_presence_share": international_share,
                "distinct_country_count": _distinct_union(
                    valid["source_resolved_country"], valid["destination_resolved_country"]
                ),
                "origin_country_count": int(valid["source_resolved_country"].nunique()),
                "destination_country_count": int(
                    valid["destination_resolved_country"].nunique()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["distinct_country_count", "airline_code"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def build_airport_connectivity(
    non_codeshare: pd.DataFrame,
    airports: pd.DataFrame,
) -> pd.DataFrame:
    geographic = non_codeshare.loc[non_codeshare["geographic_metric_eligible"]].copy()
    pairs = geographic[
        ["source_resolved_airport_id", "destination_resolved_airport_id"]
    ].drop_duplicates().rename(
        columns={
            "source_resolved_airport_id": "source_airport_id",
            "destination_resolved_airport_id": "destination_airport_id",
        }
    )
    edge_set = {
        (int(source), int(destination))
        for source, destination in pairs.itertuples(index=False, name=None)
    }

    outgoing_destinations = pairs.groupby("source_airport_id")[
        "destination_airport_id"
    ].nunique()
    incoming_origins = pairs.groupby("destination_airport_id")[
        "source_airport_id"
    ].nunique()
    outgoing_airlines = geographic.groupby("source_resolved_airport_id")[
        "airline_key"
    ].nunique()
    incoming_airlines = geographic.groupby("destination_resolved_airport_id")[
        "airline_key"
    ].nunique()

    international = geographic.loc[
        geographic["source_resolved_country"].notna()
        & geographic["destination_resolved_country"].notna()
        & geographic["source_resolved_country"].ne(geographic["destination_resolved_country"])
    ]
    international_destinations = international.groupby("source_resolved_airport_id")[
        "destination_resolved_airport_id"
    ].nunique()
    international_origins = international.groupby("destination_resolved_airport_id")[
        "source_resolved_airport_id"
    ].nunique()

    reciprocal_by_source: dict[int, float] = {}
    for source, group in pairs.groupby("source_airport_id"):
        destinations = group["destination_airport_id"].astype(int).tolist()
        reciprocal_count = sum((destination, int(source)) in edge_set for destination in destinations)
        reciprocal_by_source[int(source)] = reciprocal_count / len(destinations)

    airport_ids = sorted(
        set(pairs["source_airport_id"].astype(int))
        | set(pairs["destination_airport_id"].astype(int))
    )
    lookup = airports.set_index("airport_id", drop=False)
    rows: list[dict[str, Any]] = []
    for airport_id in airport_ids:
        airport = lookup.loc[airport_id]
        rows.append(
            {
                "airport_id": airport_id,
                "airport_key": f"id:{airport_id}",
                "airport_iata": airport["iata"],
                "airport_name": airport["name"],
                "city": airport["city"],
                "country": airport["country"],
                "outgoing_distinct_destinations": int(
                    outgoing_destinations.get(airport_id, 0)
                ),
                "incoming_distinct_origins": int(incoming_origins.get(airport_id, 0)),
                "outgoing_listed_airlines": int(outgoing_airlines.get(airport_id, 0)),
                "incoming_listed_airlines": int(incoming_airlines.get(airport_id, 0)),
                "international_destination_count": int(
                    international_destinations.get(airport_id, 0)
                ),
                "international_origin_count": int(
                    international_origins.get(airport_id, 0)
                ),
                "reciprocal_connectivity_ratio": reciprocal_by_source.get(
                    airport_id, np.nan
                ),
                "endpoint_quality_status": "canonical_resolved",
                "geographic_metric_eligible": True,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["outgoing_distinct_destinations", "airport_iata"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def _carrier_names(frame: pd.DataFrame) -> str:
    names = frame["airline_name"].fillna(frame["airline_code"]).dropna().unique()
    return "; ".join(sorted(str(name) for name in names))


def build_route_carrier_diversity(non_codeshare: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["source_airport_id", "destination_airport_id"]
    for (source_id, destination_id), group in non_codeshare.groupby(group_columns):
        canonical = bool(
            group["geographic_metric_eligible"].all()
            and group["source_resolved_airport_id"].nunique() == 1
            and group["destination_resolved_airport_id"].nunique() == 1
        )
        statuses = set(group["source_resolution_status"].dropna()) | set(
            group["destination_resolution_status"].dropna()
        )
        quality_status = "id_code_consistent"
        for candidate in ("conflicting", "unresolved", "code_only", "id_only"):
            if candidate in statuses:
                quality_status = candidate
                break
        else:
            if "resolved_by_unique_code" in statuses:
                quality_status = "resolved_by_unique_code"

        def display_value(column: str) -> Any:
            return _first_value(group, column) if canonical else pd.NA

        rows.append(
            {
                "source_airport_id": int(source_id),
                "destination_airport_id": int(destination_id),
                "source_airport_key": _first_value(group, "source_airport_key"),
                "destination_airport_key": _first_value(group, "destination_airport_key"),
                "source_iata": display_value("source_resolved_airport_code"),
                "destination_iata": display_value("destination_resolved_airport_code"),
                "source_airport_name": display_value("source_resolved_airport_name"),
                "destination_airport_name": display_value("destination_resolved_airport_name"),
                "source_country": display_value("source_resolved_country"),
                "destination_country": display_value("destination_resolved_country"),
                "source_resolution_status": _first_value(group, "source_resolution_status"),
                "destination_resolution_status": _first_value(group, "destination_resolution_status"),
                "endpoint_quality_status": quality_status,
                "geographic_metric_eligible": canonical,
                "listed_carrier_count": int(group["airline_key"].nunique()),
                "listed_carrier_names": _carrier_names(group),
                "codeshare_included": False,
                "single_listed_carrier_flag": bool(
                    group["airline_key"].nunique() == 1
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["listed_carrier_count", "source_airport_id", "destination_airport_id"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)


def _sensitivity_profile(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {
            "route_presences": 0,
            "airport_coverage": 0,
            "country_coverage": 0,
            "top1_origin_share": np.nan,
            "origin_airport_hhi": np.nan,
            "effective_hubs": np.nan,
        }
    hub = calculate_hub_values(frame)
    geographic = frame.loc[frame["geographic_metric_eligible"]]
    return {
        "route_presences": int(len(frame)),
        "airport_coverage": _distinct_union(
            geographic["source_resolved_airport_id"], geographic["destination_resolved_airport_id"]
        ),
        "country_coverage": _distinct_union(
            geographic["source_resolved_country"], geographic["destination_resolved_country"]
        ),
        "top1_origin_share": float(hub["top1_origin_share"]),
        "origin_airport_hhi": float(hub["origin_airport_hhi"]),
        "effective_hubs": float(hub["effective_hubs"]),
    }


def build_codeshare_sensitivity(
    non_codeshare: pd.DataFrame,
    all_listed: pd.DataFrame,
) -> pd.DataFrame:
    non_groups = {key: group for key, group in non_codeshare.groupby("airline_key")}
    all_groups = {key: group for key, group in all_listed.groupby("airline_key")}
    rows: list[dict[str, Any]] = []
    for airline_key in sorted(all_groups):
        all_group = all_groups[airline_key]
        non_group = non_groups.get(airline_key, all_group.iloc[0:0])
        non_profile = _sensitivity_profile(non_group)
        all_profile = _sensitivity_profile(all_group)
        metadata_source = non_group if not non_group.empty else all_group
        rows.append(
            {
                **_airline_metadata(metadata_source),
                **_comparison_flags(int(non_profile["route_presences"])),
                "non_codeshare_route_presence_count": non_profile["route_presences"],
                "all_listed_route_presence_count": all_profile["route_presences"],
                "route_presence_uplift": int(
                    all_profile["route_presences"] - non_profile["route_presences"]
                ),
                "non_codeshare_airport_coverage": non_profile["airport_coverage"],
                "all_listed_airport_coverage": all_profile["airport_coverage"],
                "airport_coverage_uplift": int(
                    all_profile["airport_coverage"] - non_profile["airport_coverage"]
                ),
                "non_codeshare_country_coverage": non_profile["country_coverage"],
                "all_listed_country_coverage": all_profile["country_coverage"],
                "country_coverage_uplift": int(
                    all_profile["country_coverage"] - non_profile["country_coverage"]
                ),
                "non_codeshare_top1_origin_share": non_profile[
                    "top1_origin_share"
                ],
                "all_listed_top1_origin_share": all_profile["top1_origin_share"],
                "top1_origin_share_difference": all_profile["top1_origin_share"]
                - non_profile["top1_origin_share"],
                "non_codeshare_origin_airport_hhi": non_profile[
                    "origin_airport_hhi"
                ],
                "all_listed_origin_airport_hhi": all_profile[
                    "origin_airport_hhi"
                ],
                "origin_hhi_difference": all_profile["origin_airport_hhi"]
                - non_profile["origin_airport_hhi"],
                "non_codeshare_effective_hubs": non_profile["effective_hubs"],
                "all_listed_effective_hubs": all_profile["effective_hubs"],
                "effective_hubs_difference": all_profile["effective_hubs"]
                - non_profile["effective_hubs"],
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["route_presence_uplift", "airline_code"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def build_dim_airline(
    non_codeshare: pd.DataFrame,
    all_listed: pd.DataFrame,
) -> pd.DataFrame:
    non_groups = {key: group for key, group in non_codeshare.groupby("airline_key")}
    rows: list[dict[str, Any]] = []
    for airline_key, all_group in all_listed.groupby("airline_key"):
        non_group = non_groups.get(airline_key, all_group.iloc[0:0])
        metadata_source = non_group if not non_group.empty else all_group
        count = int(len(non_group))
        metadata = _airline_metadata(metadata_source)
        rows.append(
            {
                "airline_key": airline_key,
                "airline_id": metadata["airline_id"],
                "airline_code": metadata["airline_code"],
                "airline_name": metadata["airline_name"],
                "airline_country": metadata["airline_country"],
                "active_status": metadata["airline_active"],
                "has_non_codeshare_routes": not non_group.empty,
                "has_all_listed_routes": not all_group.empty,
                "route_presence_count": count,
                "dashboard_comparison_eligible": count >= 50,
                **_comparison_flags(count),
            }
        )
    return pd.DataFrame(rows).sort_values("airline_key", kind="stable").reset_index(drop=True)


def build_airline_origin_detail(non_codeshare: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    airline_totals = non_codeshare.groupby("airline_key").size().to_dict()
    grouped = non_codeshare.groupby(["airline_key", "source_airport_key"], dropna=False)
    for (airline_key, origin_key), group in grouped:
        airline_total = int(airline_totals[airline_key])
        status = _first_value(group, "source_resolution_status")
        rows.append(
            {
                "airline_key": airline_key,
                "origin_airport_key": origin_key,
                "resolved_airport_code": _first_value(group, "source_resolved_airport_code"),
                "airport_name": _first_value(group, "source_resolved_airport_name"),
                "city": _first_value(group, "source_resolved_city"),
                "country": _first_value(group, "source_resolved_country"),
                "origin_route_presence_count": int(len(group)),
                "origin_route_share": float(len(group) / airline_total),
                "endpoint_quality_status": status,
                "geographic_metric_eligible": bool(group["source_geographic_eligible"].all()),
                **_comparison_flags(airline_total),
            }
        )
    detail = pd.DataFrame(rows)
    detail["rank_within_airline"] = detail.groupby("airline_key")[
        "origin_route_presence_count"
    ].rank(method="first", ascending=False).astype(int)
    return detail.sort_values(
        ["airline_key", "rank_within_airline", "origin_airport_key"], kind="stable"
    ).reset_index(drop=True)


def build_analytics_tables(
    non_codeshare: pd.DataFrame,
    all_listed: pd.DataFrame,
    airports: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    return {
        "dim_airline": build_dim_airline(non_codeshare, all_listed),
        "airline_network_summary": build_airline_network_summary(
            non_codeshare, all_listed
        ),
        "airline_hub_dependence": build_airline_hub_dependence(non_codeshare),
        "airline_geographic_reach": build_airline_geographic_reach(
            non_codeshare
        ),
        "airport_connectivity": build_airport_connectivity(
            non_codeshare, airports
        ),
        "route_carrier_diversity": build_route_carrier_diversity(
            non_codeshare
        ),
        "codeshare_sensitivity": build_codeshare_sensitivity(
            non_codeshare, all_listed
        ),
        "airline_origin_detail": build_airline_origin_detail(non_codeshare),
    }
