"""Aggregate-only, read-only quality audit for the EM2023 CSV sources."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA_RELATIVE_PATH = Path("docs/data_dictionary/source_schema.json")
TABLE_REPORT_NAME = "data_quality_audit_tables.csv"
COLUMN_REPORT_NAME = "data_quality_audit_columns.csv"


class DataQualityAuditError(RuntimeError):
    """Raised when source metadata or a CSV cannot be audited safely."""


def _row_digest(row: list[str]) -> bytes:
    digest = hashlib.blake2b(digest_size=16)
    digest.update(len(row).to_bytes(8, "big"))
    for value in row:
        encoded = value.encode("utf-8", errors="surrogatepass")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.digest()


def _is_numeric(value: str) -> bool:
    if value == "" or value.strip() == "":
        return False
    try:
        return Decimal(value.strip()).is_finite()
    except InvalidOperation:
        return False


def _load_schema(project_root: Path) -> list[dict[str, Any]]:
    schema_path = project_root / SCHEMA_RELATIVE_PATH
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DataQualityAuditError(
            f"Could not load schema {SCHEMA_RELATIVE_PATH.as_posix()} ({type(exc).__name__})"
        ) from exc
    if not isinstance(schema, list) or not schema:
        raise DataQualityAuditError("Preliminary schema must be a non-empty list")
    return schema


def audit_source_csvs(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return aggregate table and column metrics without retaining row values."""
    project_root = Path(project_root).resolve()
    schema = _load_schema(project_root)
    table_results: list[dict[str, Any]] = []
    column_results: list[dict[str, Any]] = []

    for source in schema:
        rel = Path(source["source_path"])
        path = (project_root / rel).resolve()
        raw_root = (project_root / "data/sources/raw").resolve()
        if not path.is_relative_to(raw_root):
            raise DataQualityAuditError(f"Source path is outside data/sources/raw: {rel.as_posix()}")
        encoding, delimiter = source.get("encoding"), source.get("delimiter")
        columns = source.get("columns")
        if not encoding or not delimiter or not isinstance(columns, list):
            raise DataQualityAuditError(f"Incomplete schema metadata for {rel.as_posix()}")
        headers = [column["source_name"] for column in columns]
        candidates = set(source.get("candidate_identifiers_unverified", []))
        candidate_values: dict[str, set[str]] = {name: set() for name in candidates}
        empty_counts = [0] * len(headers)
        whitespace_counts = [0] * len(headers)
        numeric_counts = [0] * len(headers)
        row_count = width_mismatches = duplicate_rows = total_empty = total_whitespace = 0
        seen_digests: set[bytes] = set()

        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                reader = csv.reader(stream, delimiter=delimiter, strict=True)
                observed_headers = next(reader, None)
                if observed_headers != headers:
                    raise ValueError("CSV header differs from source_schema.json")
                for row in reader:
                    row_count += 1
                    if len(row) != len(headers):
                        width_mismatches += 1
                    row_key = _row_digest(row)
                    if row_key in seen_digests:
                        duplicate_rows += 1
                    else:
                        seen_digests.add(row_key)
                    for index, name in enumerate(headers):
                        value = row[index] if index < len(row) else ""
                        if value == "":
                            empty_counts[index] += 1
                            total_empty += 1
                        elif value.strip() == "":
                            whitespace_counts[index] += 1
                            total_whitespace += 1
                        else:
                            if _is_numeric(value):
                                numeric_counts[index] += 1
                            if name in candidate_values:
                                candidate_values[name].add(value)
        except Exception as exc:
            raise DataQualityAuditError(
                f"Failed to audit {rel.as_posix()} ({type(exc).__name__})"
            ) from exc

        table_results.append({
            "source_path": rel.as_posix(),
            "column_count": len(headers),
            "row_count": row_count,
            "row_width_mismatch_count": width_mismatches,
            "exact_duplicate_row_count": duplicate_rows,
            "empty_cell_count": total_empty,
            "whitespace_only_cell_count": total_whitespace,
        })
        for index, name in enumerate(headers):
            candidate = name in candidates
            distinct = len(candidate_values[name]) if candidate else None
            nonempty = row_count - empty_counts[index] - whitespace_counts[index]
            column_results.append({
                "source_path": rel.as_posix(),
                "column_position": index + 1,
                "source_name": name,
                "row_count": row_count,
                "empty_cell_count": empty_counts[index],
                "whitespace_only_cell_count": whitespace_counts[index],
                "numeric_parseable_count": numeric_counts[index],
                "numeric_parseable_share": (numeric_counts[index] / nonempty) if nonempty else None,
                "is_identifier_candidate": candidate,
                "candidate_distinct_nonempty_count": distinct,
                "candidate_repeated_nonempty_count": (nonempty - distinct) if candidate else None,
                "candidate_status": source.get("candidate_status") if candidate else "not_flagged_by_name",
            })
    return table_results, column_results


def _write_temp_report(directory: Path, filename: str, rows: list[dict[str, Any]]) -> Path:
    fields = list(rows[0]) if rows else []
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8-sig", newline="", dir=directory,
        prefix=f".{filename}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def write_audit_reports(
    project_root: Path,
    table_results: list[dict[str, Any]],
    column_results: list[dict[str, Any]],
) -> tuple[Path, Path]:
    """Stage both aggregated reports, then replace outputs only after staging succeeds."""
    output_dir = Path(project_root) / "docs/data_dictionary"
    output_dir.mkdir(parents=True, exist_ok=True)
    table_path, column_path = output_dir / TABLE_REPORT_NAME, output_dir / COLUMN_REPORT_NAME
    staged: list[Path] = []
    try:
        staged.append(_write_temp_report(output_dir, TABLE_REPORT_NAME, table_results))
        staged.append(_write_temp_report(output_dir, COLUMN_REPORT_NAME, column_results))
        os.replace(staged[0], table_path)
        os.replace(staged[1], column_path)
    finally:
        for temp_path in staged:
            temp_path.unlink(missing_ok=True)
    return table_path, column_path
