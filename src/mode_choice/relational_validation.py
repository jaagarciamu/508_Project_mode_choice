"""Aggregate validation of candidate identifiers and same-name relationships."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path("docs/data_dictionary/source_schema.json")
CANDIDATE_REPORT = "relational_candidate_audit.csv"
RELATIONSHIP_REPORT = "relational_relationship_audit.csv"


class RelationalValidationError(RuntimeError):
    """Raised when metadata or a source CSV cannot be validated."""


def validate_relational_candidates(
    project_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return candidate-key and same-name relation metrics, retaining no row data."""
    project_root = Path(project_root).resolve()
    schema_path = project_root / SCHEMA_PATH
    try:
        schemas = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RelationalValidationError(
            f"Could not read {SCHEMA_PATH.as_posix()} ({type(exc).__name__})"
        ) from exc
    if not isinstance(schemas, list) or not schemas:
        raise RelationalValidationError("The preliminary schema must be a non-empty list")

    table_data: list[dict[str, Any]] = []
    candidate_report: list[dict[str, Any]] = []
    for item in schemas:
        rel = Path(item["source_path"])
        path = (project_root / rel).resolve()
        raw_root = (project_root / "data/sources/raw").resolve()
        if not path.is_relative_to(raw_root):
            raise RelationalValidationError(f"Source is outside data/sources/raw: {rel.as_posix()}")
        headers = [column["source_name"] for column in item["columns"]]
        candidates = [name for name in item.get("candidate_identifiers_unverified", []) if name in headers]
        positions = {name: headers.index(name) for name in candidates}
        values: dict[str, set[str]] = {name: set() for name in candidates}
        frequencies: dict[str, dict[str, int]] = {name: {} for name in candidates}
        counts = {name: {"empty": 0, "whitespace": 0, "rows": 0} for name in candidates}
        row_count = 0
        try:
            with path.open("r", encoding=item["encoding"], newline="") as stream:
                reader = csv.reader(stream, delimiter=item["delimiter"], strict=True)
                observed_headers = next(reader, None)
                if observed_headers != headers:
                    raise ValueError("CSV header differs from source_schema.json")
                for row in reader:
                    row_count += 1
                    for name, index in positions.items():
                        counts[name]["rows"] += 1
                        value = row[index] if index < len(row) else ""
                        if value == "":
                            counts[name]["empty"] += 1
                        elif value.strip() == "":
                            counts[name]["whitespace"] += 1
                        else:
                            values[name].add(value)
                            frequencies[name][value] = frequencies[name].get(value, 0) + 1
        except Exception as exc:
            raise RelationalValidationError(
                f"Failed to validate {rel.as_posix()} ({type(exc).__name__})"
            ) from exc

        entry = {
            "source_path": rel.as_posix(), "row_count": row_count,
            "values": values, "frequencies": frequencies, "counts": counts,
        }
        table_data.append(entry)
        for name in candidates:
            distinct = len(values[name])
            repeats = row_count - counts[name]["empty"] - counts[name]["whitespace"] - distinct
            candidate_report.append({
                "source_path": rel.as_posix(),
                "source_name": name,
                "row_count": row_count,
                "empty_count": counts[name]["empty"],
                "whitespace_only_count": counts[name]["whitespace"],
                "distinct_nonempty_count": distinct,
                "repeated_nonempty_count": repeats,
                "observed_unique_nonempty": bool(distinct and repeats == 0 and not counts[name]["empty"] and not counts[name]["whitespace"]),
                "assessment": "unique_observed" if distinct and repeats == 0 and not counts[name]["empty"] and not counts[name]["whitespace"] else "repetition_or_missing_observed",
                "candidate_status": "name_based_candidate_only; semantic_role_unconfirmed",
            })

    # Only exact candidate-name matches are considered. If exactly one side is
    # observed unique, it supplies the provisional parent direction.
    by_name: dict[str, list[tuple[dict[str, Any], set[str], dict[str, int], bool]]] = {}
    for table in table_data:
        for row in candidate_report:
            if row["source_path"] != table["source_path"]:
                continue
            name = row["source_name"]
            by_name.setdefault(name, []).append((
                table, table["values"][name], table["counts"][name],
                row["observed_unique_nonempty"], table["frequencies"][name],
            ))

    relation_report: list[dict[str, Any]] = []
    for common_name, entries in by_name.items():
        for left_index in range(len(entries)):
            for right_index in range(left_index + 1, len(entries)):
                left, right = entries[left_index], entries[right_index]
                if left[0]["source_path"] == right[0]["source_path"]:
                    continue
                if left[3] == right[3]:
                    relation_report.append(_pending_relation(left, right, common_name, "direction_ambiguous_or_no_unique_side"))
                    continue
                parent, child = (left, right) if left[3] else (right, left)
                parent_values, child_values = parent[1], child[1]
                child_nonempty_rows = child[0]["row_count"] - child[2]["empty"] - child[2]["whitespace"]
                unmatched_values = child_values - parent_values
                matched_values = child_values & parent_values
                # No row values are retained; only set membership counts are reported.
                child_unmatched_rows = sum(
                    frequency for value, frequency in child[4].items()
                    if value not in parent_values
                )
                child_matched_rows = child_nonempty_rows - child_unmatched_rows
                status = "validada" if child_unmatched_rows == 0 else "rechazada"
                relation_report.append({
                    "candidate_name": common_name,
                    "parent_source": parent[0]["source_path"],
                    "parent_column": common_name,
                    "child_source": child[0]["source_path"],
                    "child_column": common_name,
                    "parent_unique_nonempty_values": len(parent_values),
                    "child_distinct_nonempty_values": len(child_values),
                    "distinct_values_present_in_both": len(matched_values),
                    "child_distinct_values_without_parent": len(unmatched_values),
                    "child_empty_rows": child[2]["empty"],
                    "child_whitespace_only_rows": child[2]["whitespace"],
                    "child_rows_with_match": child_matched_rows,
                    "child_rows_without_match": child_unmatched_rows,
                    "parent_distinct_values_without_child": len(parent_values - child_values),
                    "validation_status": status,
                    "status_note": "empirical referential-integrity signal; semantic meaning still needs documentation",
                })
    return candidate_report, relation_report


def _pending_relation(left: tuple[Any, ...], right: tuple[Any, ...], name: str, note: str) -> dict[str, Any]:
    return {
        "candidate_name": name,
        "parent_source": "",
        "parent_column": name,
        "child_source": "",
        "child_column": name,
        "parent_unique_nonempty_values": None,
        "child_distinct_nonempty_values": None,
        "distinct_values_present_in_both": None,
        "child_distinct_values_without_parent": None,
        "child_empty_rows": None,
        "child_whitespace_only_rows": None,
        "child_rows_with_match": None,
        "child_rows_without_match": None,
        "parent_distinct_values_without_child": None,
        "validation_status": "pendiente",
        "status_note": note,
        "source_a": left[0]["source_path"],
        "source_b": right[0]["source_path"],
    }


def write_relational_reports(
    project_root: Path,
    candidate_results: list[dict[str, Any]],
    relationship_results: list[dict[str, Any]],
) -> tuple[Path, Path]:
    """Stage reports and publish them after validation has completed successfully."""
    output_dir = Path(project_root) / "docs/data_dictionary"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / CANDIDATE_REPORT, output_dir / RELATIONSHIP_REPORT]
    staged: list[Path] = []
    try:
        for destination, rows in zip(outputs, (candidate_results, relationship_results), strict=True):
            fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else ["validation_status"]
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8-sig", newline="", dir=output_dir,
                prefix=f".{destination.name}.", suffix=".tmp", delete=False,
            ) as stream:
                staged_path = Path(stream.name)
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            staged.append(staged_path)
        for staged_path, destination in zip(staged, outputs, strict=True):
            os.replace(staged_path, destination)
    finally:
        for path in staged:
            path.unlink(missing_ok=True)
    return outputs[0], outputs[1]
