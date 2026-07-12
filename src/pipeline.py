from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import (
    ANALYTICS_DIR,
    ANALYTICS_TABLES,
    CHECKSUM_MANIFEST,
    DATABASE_PATH,
    PROCESSED_DIR,
    PROCESSED_OUTPUTS,
    RAW_DIR,
)
from .database import write_sqlite_database
from .loaders import load_raw_tables, verify_raw_checksums
from .metrics import build_analytics_tables
from .resolution import resolve_route_endpoints
from .transform import build_enriched_routes, prepare_route_presences


def _json_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        path,
        index=False,
        lineterminator="\n",
        float_format="%.15g",
    )


def clean_generated_outputs() -> None:
    for filename in PROCESSED_OUTPUTS:
        path = PROCESSED_DIR / filename
        if path.exists():
            path.unlink()
    if ANALYTICS_DIR.exists():
        for path in ANALYTICS_DIR.iterdir():
            if path.is_file():
                path.unlink()


def run_pipeline(*, clean: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    checksums = verify_raw_checksums(RAW_DIR, CHECKSUM_MANIFEST)
    if clean:
        clean_generated_outputs()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

    airports, airlines, routes = load_raw_tables(RAW_DIR)
    enriched, quality = build_enriched_routes(airports, airlines, routes)
    enriched, endpoint_quality = resolve_route_endpoints(enriched, airports)
    quality.update(endpoint_quality)
    all_listed = prepare_route_presences(enriched, include_codeshare=True)
    non_codeshare = prepare_route_presences(enriched, include_codeshare=False)

    quality.update(
        {
            "all_listed_valid_directed_route_presences": int(len(all_listed)),
            "non_codeshare_valid_directed_route_presences": int(
                len(non_codeshare)
            ),
            "distance_valid_non_codeshare_route_presences": int(
                non_codeshare["geographic_metric_eligible"].sum()
            ),
            "geographic_excluded_non_codeshare_route_presences": int(
                (~non_codeshare["geographic_metric_eligible"]).sum()
            ),
            "airport_5613_geographic_eligible_rows": int(
                (
                    (
                        non_codeshare["source_airport_id"].eq(5613)
                        | non_codeshare["destination_airport_id"].eq(5613)
                    )
                    & non_codeshare["geographic_metric_eligible"]
                ).sum()
            ),
        }
    )

    analytics = build_analytics_tables(non_codeshare, all_listed, airports)
    if list(analytics) != ANALYTICS_TABLES:
        raise AssertionError("Analytics table set does not match the configured contract")

    processed = {
        "airports_clean": airports,
        "airlines_clean": airlines,
        "routes_clean": routes,
        "routes_enriched": enriched,
    }
    for name, frame in processed.items():
        _write_csv(frame, PROCESSED_DIR / f"{name}.csv")
    for name, frame in analytics.items():
        _write_csv(frame, ANALYTICS_DIR / f"{name}.csv")

    output_shapes = {
        name: {"rows": int(len(frame)), "columns": int(len(frame.columns))}
        for name, frame in analytics.items()
    }
    quality_document = {
        "dataset": "OpenFlights 2014 historical route snapshot",
        "analysis_unit": "directed airline-origin-destination route presence",
        "primary_network": "non-codeshare route presences (operating-network proxy)",
        "raw_checksums": checksums,
        "quality_metrics": {key: _json_value(value) for key, value in quality.items()},
        "analytics_output_shapes": output_shapes,
    }
    (ANALYTICS_DIR / "data_quality.json").write_text(
        json.dumps(quality_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    database_tables = {
        **processed,
        "route_presences_all_listed": all_listed,
        "route_presences_non_codeshare": non_codeshare,
        **analytics,
        "data_quality_metrics": pd.DataFrame(
            [
                {
                    "metric": key,
                    "value": (
                        json.dumps(value, sort_keys=True)
                        if isinstance(value, dict)
                        else _json_value(value)
                    ),
                }
                for key, value in sorted(quality.items())
            ]
        ),
    }
    write_sqlite_database(DATABASE_PATH, database_tables)

    elapsed_seconds = time.perf_counter() - started
    summary = {
        "elapsed_seconds": elapsed_seconds,
        "quality": quality,
        "outputs": output_shapes,
        "database": str(DATABASE_PATH),
    }
    print("Pipeline completed successfully")
    print(f"Elapsed seconds: {elapsed_seconds:.3f}")
    for name, shape in output_shapes.items():
        print(f"{name}: {shape['rows']} rows x {shape['columns']} columns")
    print(f"SQLite database: {DATABASE_PATH}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build OpenFlights route-presence analytics outputs."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove only generated processed/analytics outputs before rebuilding.",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    run_pipeline(clean=arguments.clean)


if __name__ == "__main__":
    main()
