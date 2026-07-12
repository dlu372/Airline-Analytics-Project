from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


CANONICAL_ENDPOINT_STATUSES = {
    "id_code_consistent",
    "resolved_by_unique_code",
    "conflicting",
}


def _normalise_code(value: Any) -> str | None:
    if pd.isna(value):
        return None
    code = str(value).strip().upper()
    return code or None


def _normalise_id(value: Any) -> int | None:
    if pd.isna(value):
        return None
    return int(value)


def structural_airport_key(airport_id: Any, airport_code: Any) -> str:
    normalised_id = _normalise_id(airport_id)
    if normalised_id is not None:
        return f"id:{normalised_id}"
    code = _normalise_code(airport_code)
    return f"code:{code}" if code else "unresolved"


def _build_indexes(
    airports: pd.DataFrame,
) -> tuple[dict[int, dict[str, Any]], dict[str, set[int]]]:
    by_id: dict[int, dict[str, Any]] = {}
    by_code: dict[str, set[int]] = defaultdict(set)
    for row in airports.to_dict("records"):
        airport_id = _normalise_id(row["airport_id"])
        if airport_id is None:
            continue
        by_id[airport_id] = row
        for field in ("iata", "icao"):
            code = _normalise_code(row[field])
            if code:
                by_code[code].add(airport_id)
    return by_id, by_code


def _resolve_one(
    airport_id: Any,
    airport_code: Any,
    by_id: dict[int, dict[str, Any]],
    by_code: dict[str, set[int]],
) -> tuple[str, dict[str, Any] | None]:
    normalised_id = _normalise_id(airport_id)
    code = _normalise_code(airport_code)
    id_record = by_id.get(normalised_id) if normalised_id is not None else None
    code_ids = by_code.get(code, set()) if code else set()

    if id_record is not None:
        id_codes = {
            _normalise_code(id_record["iata"]),
            _normalise_code(id_record["icao"]),
        } - {None}
        if code in id_codes:
            return "id_code_consistent", id_record
        if len(code_ids) == 1 and normalised_id not in code_ids:
            return "conflicting", by_id[next(iter(code_ids))]
        return "id_only", None

    if len(code_ids) == 1:
        return "resolved_by_unique_code", by_id[next(iter(code_ids))]
    if len(code_ids) > 1:
        return "code_only", None
    return "unresolved", None


def _valid_coordinates(record: dict[str, Any] | None) -> bool:
    if record is None:
        return False
    latitude = record["latitude"]
    longitude = record["longitude"]
    return bool(
        pd.notna(latitude)
        and pd.notna(longitude)
        and -90 <= float(latitude) <= 90
        and -180 <= float(longitude) <= 180
    )


def resolve_route_endpoints(
    routes: pd.DataFrame,
    airports: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Resolve endpoint identity without overwriting raw IDs or codes.

    The canonical geographic policy is unique-code-first because the route
    snapshot's code is temporally aligned with the route record. A conflict is
    resolved to the unique code target but remains explicitly flagged; no raw
    ID or code is overwritten. ID-only and unresolved endpoints are excluded.
    """
    frame = routes.copy()
    by_id, by_code = _build_indexes(airports)

    strategy_counts = {"airport_id_first": 0, "unique_code_first": 0, "strict_consensus": 0}
    endpoint_counts: dict[str, dict[str, int]] = {}
    for side, raw_code_column in (
        ("source", "source_airport"),
        ("destination", "destination_airport"),
    ):
        records: list[dict[str, Any]] = []
        statuses: list[str] = []
        eligible: list[bool] = []
        structural_keys: list[str] = []
        for airport_id, airport_code in frame[
            [f"{side}_airport_id", raw_code_column]
        ].itertuples(index=False, name=None):
            status, record = _resolve_one(airport_id, airport_code, by_id, by_code)
            statuses.append(status)
            records.append(record or {})
            eligible.append(status in CANONICAL_ENDPOINT_STATUSES and _valid_coordinates(record))
            structural_keys.append(structural_airport_key(airport_id, airport_code))

        frame[f"{side}_airport_key"] = pd.Series(
            structural_keys, index=frame.index, dtype="string"
        )
        frame[f"{side}_resolution_status"] = pd.Series(
            statuses, index=frame.index, dtype="string"
        )
        frame[f"{side}_geographic_eligible"] = pd.Series(
            eligible, index=frame.index, dtype=bool
        )
        resolved = pd.DataFrame(records, index=frame.index)
        field_map = {
            "airport_id": "resolved_airport_id",
            "name": "resolved_airport_name",
            "city": "resolved_city",
            "country": "resolved_country",
            "latitude": "resolved_latitude",
            "longitude": "resolved_longitude",
        }
        for source_field, suffix in field_map.items():
            values = resolved[source_field] if source_field in resolved else pd.NA
            frame[f"{side}_{suffix}"] = values
        if not resolved.empty:
            resolved_code = resolved.get("iata", pd.Series(pd.NA, index=frame.index)).fillna(
                resolved.get("icao", pd.Series(pd.NA, index=frame.index))
            )
        else:
            resolved_code = pd.Series(pd.NA, index=frame.index)
        frame[f"{side}_resolved_airport_code"] = resolved_code.astype("string")
        frame[f"{side}_resolved_airport_key"] = frame[f"{side}_resolved_airport_id"].map(
            lambda value: f"id:{int(value)}" if pd.notna(value) else pd.NA
        ).astype("string")
        endpoint_counts[side] = {
            key: int(value)
            for key, value in frame[f"{side}_resolution_status"].value_counts().sort_index().items()
        }

    frame["geographic_metric_eligible"] = (
        frame["source_geographic_eligible"] & frame["destination_geographic_eligible"]
    )

    def combined_status(source: str, destination: str) -> str:
        if source == destination == "id_code_consistent":
            return "id_code_consistent"
        for status in ("conflicting", "unresolved", "code_only", "id_only"):
            if status in (source, destination):
                return status
        if source in CANONICAL_ENDPOINT_STATUSES and destination in CANONICAL_ENDPOINT_STATUSES:
            return "resolved_by_unique_code"
        return "unresolved"

    frame["endpoint_quality_status"] = pd.Series(
        [
            combined_status(source, destination)
            for source, destination in frame[
                ["source_resolution_status", "destination_resolution_status"]
            ].itertuples(index=False, name=None)
        ],
        index=frame.index,
        dtype="string",
    )

    source_id_known = frame["source_airport_id"].isin(by_id)
    destination_id_known = frame["destination_airport_id"].isin(by_id)
    source_code_unique = frame["source_airport"].map(
        lambda value: len(by_code.get(_normalise_code(value), set())) == 1
    )
    destination_code_unique = frame["destination_airport"].map(
        lambda value: len(by_code.get(_normalise_code(value), set())) == 1
    )
    strategy_counts["airport_id_first"] = int((source_id_known & destination_id_known).sum())
    strategy_counts["unique_code_first"] = int((source_code_unique & destination_code_unique).sum())
    strategy_counts["strict_consensus"] = int(
        (
            frame["source_resolution_status"].eq("id_code_consistent")
            & frame["destination_resolution_status"].eq("id_code_consistent")
        ).sum()
    )
    strategy_counts["canonical_unique_code_first"] = int(
        frame["geographic_metric_eligible"].sum()
    )
    quality = {
        "endpoint_resolution_status_counts": endpoint_counts,
        "endpoint_strategy_route_counts": strategy_counts,
        "canonical_geographic_route_rows": int(frame["geographic_metric_eligible"].sum()),
        "excluded_geographic_route_rows": int((~frame["geographic_metric_eligible"]).sum()),
    }
    return frame, quality
