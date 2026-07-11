from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd


def write_sqlite_database(
    database_path: Path,
    tables: dict[str, pd.DataFrame],
) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")
    if temporary_path.exists():
        temporary_path.unlink()

    connection = sqlite3.connect(temporary_path)
    try:
        for name, frame in tables.items():
            frame.to_sql(name, connection, if_exists="replace", index=False)

        connection.executescript(
            """
            CREATE INDEX idx_routes_enriched_airline_od
            ON routes_enriched (airline_key, source_airport_id, destination_airport_id);

            CREATE INDEX idx_route_presence_non_codeshare_airline
            ON route_presences_non_codeshare (airline_key);

            CREATE INDEX idx_route_presence_non_codeshare_source
            ON route_presences_non_codeshare (source_airport_id);

            CREATE INDEX idx_route_presence_non_codeshare_destination
            ON route_presences_non_codeshare (destination_airport_id);

            CREATE INDEX idx_route_carrier_diversity_od
            ON route_carrier_diversity (source_airport_id, destination_airport_id);
            """
        )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        connection.commit()
    finally:
        connection.close()

    os.replace(temporary_path, database_path)
