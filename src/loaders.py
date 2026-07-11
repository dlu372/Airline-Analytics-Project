from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .config import AIRLINE_COLUMNS, AIRPORT_COLUMNS, ROUTE_COLUMNS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_raw_checksums(raw_dir: Path, manifest_path: Path) -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        checksum, filename = line.split(maxsplit=1)
        expected[Path(filename.strip()).name] = checksum

    required = {"airports.dat", "airlines.dat", "routes.dat"}
    if set(expected) != required:
        raise ValueError(
            f"Checksum manifest must contain exactly {sorted(required)}; "
            f"found {sorted(expected)}"
        )

    actual: dict[str, str] = {}
    for filename, expected_hash in sorted(expected.items()):
        path = raw_dir / filename
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"Checksum mismatch for {filename}: "
                f"expected {expected_hash}, found {actual_hash}"
            )
        actual[filename] = actual_hash
    return actual


def _read_as_strings(path: Path, columns: list[str]) -> pd.DataFrame:
    return pd.read_csv(
        path,
        header=None,
        names=columns,
        dtype="string",
        keep_default_na=True,
        na_values=[r"\N"],
    )


def _to_nullable_integer(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")


def _to_nullable_float(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")


def load_raw_tables(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    airports = _read_as_strings(raw_dir / "airports.dat", AIRPORT_COLUMNS)
    airlines = _read_as_strings(raw_dir / "airlines.dat", AIRLINE_COLUMNS)
    routes = _read_as_strings(raw_dir / "routes.dat", ROUTE_COLUMNS)

    _to_nullable_integer(airports, ["airport_id", "altitude"])
    _to_nullable_float(airports, ["latitude", "longitude", "timezone"])
    _to_nullable_integer(airlines, ["airline_id"])
    _to_nullable_integer(
        routes,
        ["airline_id", "source_airport_id", "destination_airport_id", "stops"],
    )

    routes["codeshare"] = routes["codeshare"].fillna("").str.strip()
    routes["is_codeshare"] = routes["codeshare"].eq("Y")

    return airports, airlines, routes
