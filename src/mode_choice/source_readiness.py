"""Read-only technical readiness checks for the EM2023 source CSV files."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any


PRIMARY_KEY_FIELDS = {
    "a. Modulo hogares.csv": "key_hg",
    "b. Modulo vehiculos.csv": "cod_vh",
    "c. Modulo personas.csv": "key_persona",
    "d. Modulo viajes.csv": "key_viaje",
    "e. Modulo etapas.csv": "key_etapa",
}


class SourceReadinessError(RuntimeError):
    """Raised when a source file cannot be read or conflicts with its schema."""


def inspect_source_readiness(project_root: Path) -> list[dict[str, Any]]:
    """Read sources as text and return aggregate checks without changing data."""
    project_root = Path(project_root).resolve()
    schema_path = project_root / "docs/data_dictionary/source_schema.json"
    inventory_path = project_root / "docs/data_dictionary/source_inventory.csv"
    try:
        schemas = json.loads(schema_path.read_text(encoding="utf-8"))
        with inventory_path.open(encoding="utf-8-sig", newline="") as stream:
            inventory_rows = list(csv.DictReader(stream))
    except Exception as exc:
        raise SourceReadinessError(
            f"Could not load the source catalog ({type(exc).__name__})"
        ) from exc

    csv_inventory = {
        row["source_path"]: row for row in inventory_rows if row.get("format") == "csv"
    }
    if len(schemas) != len(PRIMARY_KEY_FIELDS):
        raise SourceReadinessError(
            f"Expected {len(PRIMARY_KEY_FIELDS)} CSV schemas; found {len(schemas)}"
        )
    schema_paths = {item.get("source_path") for item in schemas}
    if schema_paths != set(csv_inventory):
        raise SourceReadinessError("CSV paths in source_schema.json and source_inventory.csv differ")

    results: list[dict[str, Any]] = []
    for item in schemas:
        relative_path = item["source_path"]
        source_path = (project_root / relative_path).resolve()
        raw_root = (project_root / "data/sources/raw").resolve()
        if not source_path.is_relative_to(raw_root):
            raise SourceReadinessError(f"Source path is outside data/sources/raw: {relative_path}")
        inventory_row = csv_inventory[relative_path]
        if inventory_row.get("csv_encoding") != item.get("encoding") or inventory_row.get("csv_delimiter") != item.get("delimiter"):
            raise SourceReadinessError(f"Catalog settings differ for {relative_path}")

        source_columns = item.get("columns", [])
        headers = [column["source_name"] for column in source_columns]
        primary_field = PRIMARY_KEY_FIELDS.get(source_path.name)
        if primary_field not in headers:
            raise SourceReadinessError(f"Expected technical key field is missing in {relative_path}")
        key_position = headers.index(primary_field)
        key_values: set[str] = set()
        row_count = width_mismatch_count = key_empty_count = key_whitespace_count = 0
        try:
            with source_path.open("r", encoding=item["encoding"], newline="") as stream:
                reader = csv.reader(stream, delimiter=item["delimiter"], strict=True)
                observed_headers = next(reader, None)
                if observed_headers != headers:
                    raise ValueError("Source header differs from source_schema.json")
                for row in reader:
                    row_count += 1
                    if len(row) != len(headers):
                        width_mismatch_count += 1
                    key_value = row[key_position] if key_position < len(row) else ""
                    if key_value == "":
                        key_empty_count += 1
                    elif key_value.strip() == "":
                        key_whitespace_count += 1
                    else:
                        key_values.add(key_value)
        except Exception as exc:
            raise SourceReadinessError(
                f"Failed to inspect {relative_path} ({type(exc).__name__})"
            ) from exc

        key_duplicate_count = row_count - key_empty_count - key_whitespace_count - len(key_values)
        ready = (
            width_mismatch_count == 0
            and key_empty_count == 0
            and key_whitespace_count == 0
            and key_duplicate_count == 0
        )
        results.append({
            "source_path": relative_path,
            "source_encoding": item["encoding"],
            "source_delimiter": item["delimiter"],
            "source_column_count": len(headers),
            "source_row_count": row_count,
            "header_matches_schema": True,
            "row_width_mismatch_count": width_mismatch_count,
            "technical_key_field": primary_field,
            "technical_key_empty_count": key_empty_count,
            "technical_key_whitespace_only_count": key_whitespace_count,
            "technical_key_duplicate_count": key_duplicate_count,
            "all_source_values_read_as_text": True,
            "readiness_status": "ready" if ready else "review_required",
        })
    return results


def write_readiness_report(project_root: Path, results: list[dict[str, Any]]) -> Path:
    """Write aggregate readiness metrics after all source files pass inspection."""
    output_path = Path(project_root) / "docs/data_dictionary/standardization_readiness.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(results[0]) if results else ["readiness_status"]
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return output_path
