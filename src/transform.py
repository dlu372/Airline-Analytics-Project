from __future__ import annotations

from typing import Any

import pandas as pd

from .config import EXPECTED_ROUTE_ROWS


def _airline_key(frame: pd.DataFrame) -> pd.Series:
    id_key = "id:" + frame["airline_id"].astype("string")
    code_key = "code:" + frame["airline_code"].str.strip().str.upper().fillna("UNKNOWN")
    return id_key.fillna(code_key)


def build_enriched_routes(
    airports: pd.DataFrame,
    airlines: pd.DataFrame,
    routes: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if len(routes) != EXPECTED_ROUTE_ROWS:
        raise AssertionError(
            f"Expected {EXPECTED_ROUTE_ROWS} raw route rows, found {len(routes)}"
        )

    airport_non_null = airports["airport_id"].dropna()
    airline_non_null = airlines["airline_id"].dropna()
    if airport_non_null.duplicated().any():
        raise AssertionError("airport_id must be unique in airports.dat")
    if airline_non_null.duplicated().any():
        raise AssertionError("airline_id must be unique in airlines.dat")

    source_lookup = airports[
        ["airport_id", "name", "city", "country", "iata", "latitude", "longitude"]
    ].rename(
        columns={
            "airport_id": "source_airport_id",
            "name": "source_airport_name",
            "city": "source_city",
            "country": "source_country",
            "iata": "source_iata",
            "latitude": "source_latitude",
            "longitude": "source_longitude",
        }
    )
    destination_lookup = airports[
        ["airport_id", "name", "city", "country", "iata", "latitude", "longitude"]
    ].rename(
        columns={
            "airport_id": "destination_airport_id",
            "name": "destination_airport_name",
            "city": "destination_city",
            "country": "destination_country",
            "iata": "destination_iata",
            "latitude": "destination_latitude",
            "longitude": "destination_longitude",
        }
    )
    airline_lookup = airlines[["airline_id", "name", "country", "active"]].rename(
        columns={
            "name": "airline_name",
            "country": "airline_country",
            "active": "airline_active",
        }
    )

    enriched = routes.merge(
        source_lookup,
        on="source_airport_id",
        how="left",
        validate="many_to_one",
    )
    enriched = enriched.merge(
        destination_lookup,
        on="destination_airport_id",
        how="left",
        validate="many_to_one",
    )
    enriched = enriched.merge(
        airline_lookup,
        on="airline_id",
        how="left",
        validate="many_to_one",
    )
    enriched.insert(0, "airline_key", _airline_key(enriched))

    if len(enriched) != len(routes):
        raise AssertionError("Enrichment joins changed the raw route row count")

    valid_key_rows = enriched.dropna(
        subset=["source_airport_id", "destination_airport_id"]
    )
    duplicate_directed_keys = int(
        valid_key_rows.duplicated(
            ["airline_key", "source_airport_id", "destination_airport_id"]
        ).sum()
    )
    source_equals_destination = int(
        (
            valid_key_rows["source_airport_id"]
            == valid_key_rows["destination_airport_id"]
        ).sum()
    )

    source_lat_invalid = enriched["source_latitude"].notna() & ~enriched[
        "source_latitude"
    ].between(-90, 90)
    destination_lat_invalid = enriched["destination_latitude"].notna() & ~enriched[
        "destination_latitude"
    ].between(-90, 90)
    source_lon_invalid = enriched["source_longitude"].notna() & ~enriched[
        "source_longitude"
    ].between(-180, 180)
    destination_lon_invalid = enriched["destination_longitude"].notna() & ~enriched[
        "destination_longitude"
    ].between(-180, 180)

    airline_matches = int(enriched["airline_name"].notna().sum())
    codeshare_count = int(enriched["is_codeshare"].sum())
    quality: dict[str, Any] = {
        "raw_route_row_count": int(len(routes)),
        "enriched_route_row_count": int(len(enriched)),
        "airport_id_unique": True,
        "airline_id_unique": True,
        "airline_id_matched_rows": airline_matches,
        "airline_id_unmatched_rows": int(len(enriched) - airline_matches),
        "airline_id_match_rate": airline_matches / len(enriched),
        "missing_source_iata_count": int(enriched["source_iata"].isna().sum()),
        "missing_destination_iata_count": int(
            enriched["destination_iata"].isna().sum()
        ),
        "missing_source_airport_match_count": int(
            enriched["source_airport_name"].isna().sum()
        ),
        "missing_destination_airport_match_count": int(
            enriched["destination_airport_name"].isna().sum()
        ),
        "codeshare_count": codeshare_count,
        "codeshare_share": codeshare_count / len(enriched),
        "duplicate_directed_route_key_count": duplicate_directed_keys,
        "source_equals_destination_count": source_equals_destination,
        "missing_source_coordinates_count": int(
            (enriched["source_latitude"].isna() | enriched["source_longitude"].isna()).sum()
        ),
        "missing_destination_coordinates_count": int(
            (
                enriched["destination_latitude"].isna()
                | enriched["destination_longitude"].isna()
            ).sum()
        ),
        "invalid_latitude_count": int(
            source_lat_invalid.sum() + destination_lat_invalid.sum()
        ),
        "invalid_longitude_count": int(
            source_lon_invalid.sum() + destination_lon_invalid.sum()
        ),
    }
    return enriched, quality


def prepare_route_presences(
    enriched: pd.DataFrame,
    *,
    include_codeshare: bool,
) -> pd.DataFrame:
    frame = enriched.copy()
    if not include_codeshare:
        frame = frame.loc[~frame["is_codeshare"]].copy()

    frame = frame.dropna(
        subset=[
            "source_airport_id",
            "destination_airport_id",
            "source_airport_name",
            "destination_airport_name",
        ]
    )
    frame = frame.loc[
        frame["source_airport_id"] != frame["destination_airport_id"]
    ].copy()
    frame = frame.drop_duplicates(
        ["airline_key", "source_airport_id", "destination_airport_id"],
        keep="first",
    )
    return frame.sort_values(
        ["airline_key", "source_airport_id", "destination_airport_id"],
        kind="stable",
    ).reset_index(drop=True)
