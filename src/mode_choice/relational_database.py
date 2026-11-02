"""Build a local SQLite layer while preserving source CSV fields as text."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


DATABASE_RELATIVE_PATH = Path("data/relational/em2023_relational.sqlite")
TABLE_REPORT_NAME = "relational_database_tables.csv"
RELATIONSHIP_REPORT_NAME = "relational_database_relationships.csv"

TABLE_SPECS: dict[str, dict[str, Any]] = {
    "a. Modulo hogares.csv": {
        "table": "hogares", "primary_key": "key_hg", "unique_fields": ["cod_hog"],
        "composite_unique": [("cod_hog", "key_hg")],
    },
    "b. Modulo vehiculos.csv": {
        "table": "vehiculos", "primary_key": "cod_vh", "unique_fields": [],
        "composite_unique": [],
    },
    "c. Modulo personas.csv": {
        "table": "personas", "primary_key": "key_persona", "unique_fields": ["cod_per"],
        "composite_unique": [("cod_per", "key_persona")],
    },
    "d. Modulo viajes.csv": {
        "table": "viajes", "primary_key": "key_viaje", "unique_fields": ["cod_vj"],
        "composite_unique": [("cod_vj", "key_viaje")],
    },
    "e. Modulo etapas.csv": {
        "table": "etapas", "primary_key": "key_etapa", "unique_fields": ["cod_eta"],
        "composite_unique": [],
    },
}

FOREIGN_KEY_SPECS = [
    {"child": "vehiculos", "child_fields": ("cod_hog", "key_hg"), "parent": "hogares", "parent_fields": ("cod_hog", "key_hg")},
    {"child": "personas", "child_fields": ("cod_hg", "key_hg"), "parent": "hogares", "parent_fields": ("cod_hog", "key_hg")},
    {"child": "viajes", "child_fields": ("cod_hg", "key_hg"), "parent": "hogares", "parent_fields": ("cod_hog", "key_hg")},
    {"child": "viajes", "child_fields": ("cod_pers", "key_pers"), "parent": "personas", "parent_fields": ("cod_per", "key_persona")},
    {"child": "etapas", "child_fields": ("cod_vj", "key_viaje"), "parent": "viajes", "parent_fields": ("cod_vj", "key_viaje")},
    {"child": "etapas", "child_fields": ("cod_pers",), "parent": "personas", "parent_fields": ("cod_per",)},
]

LOAD_ORDER = ("hogares", "vehiculos", "personas", "viajes", "etapas")


class RelationalDatabaseError(RuntimeError):
    """Raised when source CSVs cannot be loaded or relational checks fail."""


def quote_identifier(identifier: str) -> str:
    """Quote a SQLite identifier, including the empty source header."""
    return '"' + identifier.replace('"', '""') + '"'


def _load_schema(project_root: Path) -> list[dict[str, Any]]:
    try:
        result = json.loads((project_root / "docs/data_dictionary/source_schema.json").read_text(encoding="utf-8"))
    except Exception as exc:
        raise RelationalDatabaseError(f"Could not load source_schema.json ({type(exc).__name__})") from exc
    if not isinstance(result, list) or not result:
        raise RelationalDatabaseError("source_schema.json must contain a non-empty list")
    return result


def _create_table_sql(table: str, columns: list[str], spec: dict[str, Any]) -> str:
    key_fields = {spec["primary_key"], *spec["unique_fields"]}
    for foreign_key in FOREIGN_KEY_SPECS:
        if foreign_key["child"] == table:
            key_fields.update(foreign_key["child_fields"])
    definitions = [
        f"{quote_identifier(name)} TEXT" + (" NOT NULL" if name in key_fields else "")
        for name in columns
    ]
    constraints = [f"PRIMARY KEY ({quote_identifier(spec['primary_key'])})"]
    constraints.extend(f"UNIQUE ({quote_identifier(name)})" for name in spec["unique_fields"])
    constraints.extend(
        "UNIQUE (" + ", ".join(quote_identifier(name) for name in field_tuple) + ")"
        for field_tuple in spec["composite_unique"]
    )
    for foreign_key in FOREIGN_KEY_SPECS:
        if foreign_key["child"] != table:
            continue
        child_fields = ", ".join(quote_identifier(name) for name in foreign_key["child_fields"])
        parent_fields = ", ".join(quote_identifier(name) for name in foreign_key["parent_fields"])
        constraints.append(
            f"FOREIGN KEY ({child_fields}) REFERENCES {quote_identifier(foreign_key['parent'])} ({parent_fields})"
        )
    body = ",\n  ".join([*definitions, *constraints])
    return f"CREATE TABLE {quote_identifier(table)} (\n  {body}\n)"


def build_relational_database(project_root: Path) -> tuple[Path, list[dict[str, Any]], list[dict[str, Any]]]:
    """Build and validate the SQLite database before replacing the prior output."""
    project_root = Path(project_root).resolve()
    schemas = _load_schema(project_root)
    by_table: dict[str, dict[str, Any]] = {}
    raw_root = (project_root / "data/sources/raw").resolve()
    for item in schemas:
        source_path = (project_root / item["source_path"]).resolve()
        if not source_path.is_relative_to(raw_root):
            raise RelationalDatabaseError(f"Source path is outside data/sources/raw: {item['source_path']}")
        spec = TABLE_SPECS.get(source_path.name)
        if spec is None or spec["table"] in by_table:
            raise RelationalDatabaseError(f"Unexpected or duplicate source table: {source_path.name}")
        columns = [column["source_name"] for column in item.get("columns", [])]
        required_fields = {spec["primary_key"], *spec["unique_fields"]}
        for foreign_key in FOREIGN_KEY_SPECS:
            if foreign_key["child"] == spec["table"]:
                required_fields.update(foreign_key["child_fields"])
        if not required_fields.issubset(columns):
            raise RelationalDatabaseError(f"Required relational fields are missing in {item['source_path']}")
        by_table[spec["table"]] = {"schema": item, "path": source_path, "columns": columns, "spec": spec}
    if set(by_table) != set(LOAD_ORDER):
        raise RelationalDatabaseError("The five expected source tables are not all present in source_schema.json")

    output_path = project_root / DATABASE_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        dir=output_path.parent, prefix=".em2023_relational.", suffix=".sqlite.tmp", delete=False
    )
    temporary_path = Path(handle.name)
    handle.close()
    table_results: list[dict[str, Any]] = []
    relationship_results: list[dict[str, Any]] = []
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(temporary_path)
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RelationalDatabaseError("SQLite foreign-key enforcement could not be enabled")
        for table in LOAD_ORDER:
            info = by_table[table]
            connection.execute(_create_table_sql(table, info["columns"], info["spec"]))

        connection.execute("BEGIN")
        for table in LOAD_ORDER:
            info = by_table[table]
            item, source_path, columns, spec = info["schema"], info["path"], info["columns"], info["spec"]
            insert_sql = (
                f"INSERT INTO {quote_identifier(table)} ("
                + ", ".join(quote_identifier(name) for name in columns)
                + ") VALUES ("
                + ", ".join("?" for _ in columns)
                + ")"
            )
            row_count = width_mismatches = 0
            batch: list[list[str]] = []
            try:
                with source_path.open("r", encoding=item["encoding"], newline="") as stream:
                    reader = csv.reader(stream, delimiter=item["delimiter"], strict=True)
                    observed_headers = next(reader, None)
                    if observed_headers != columns:
                        raise ValueError("CSV header differs from source_schema.json")
                    for row in reader:
                        row_count += 1
                        if len(row) != len(columns):
                            width_mismatches += 1
                            raise ValueError("CSV row width differs from its header")
                        batch.append(row)
                        if len(batch) >= 5000:
                            connection.executemany(insert_sql, batch)
                            batch.clear()
                    if batch:
                        connection.executemany(insert_sql, batch)
            except Exception as exc:
                raise RelationalDatabaseError(
                    f"Failed to load {item['source_path']} ({type(exc).__name__})"
                ) from exc
            table_results.append({
                "table_name": table,
                "source_path": item["source_path"],
                "source_row_count": row_count,
                "loaded_row_count": row_count,
                "source_column_count": len(columns),
                "source_headers_preserved": True,
                "stored_column_type": "TEXT",
                "primary_key_field": spec["primary_key"],
                "alternate_unique_fields_json": json.dumps(spec["unique_fields"], ensure_ascii=False),
                "row_width_mismatch_count": width_mismatches,
                "status": "loaded",
            })
        connection.commit()

        for table, info in by_table.items():
            loaded_columns = [row[1] for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})")]
            declared_types = [row[2].upper() for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})")]
            if loaded_columns != info["columns"] or any(column_type != "TEXT" for column_type in declared_types):
                raise RelationalDatabaseError(f"SQLite schema validation failed for table {table}")
            count = connection.execute(f"SELECT COUNT(*) FROM {quote_identifier(table)}").fetchone()[0]
            expected = next(row["source_row_count"] for row in table_results if row["table_name"] == table)
            if count != expected:
                raise RelationalDatabaseError(f"SQLite row-count validation failed for table {table}")

        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RelationalDatabaseError(
                f"SQLite foreign-key validation found {len(foreign_key_errors)} violating rows"
            )
        integrity_results = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        if integrity_results != ["ok"]:
            raise RelationalDatabaseError("SQLite integrity_check did not return ok")
        for index, foreign_key in enumerate(FOREIGN_KEY_SPECS, start=1):
            child_count = connection.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(foreign_key['child'])}"
            ).fetchone()[0]
            relationship_results.append({
                "child_table": foreign_key["child"],
                "child_fields_json": json.dumps(foreign_key["child_fields"], ensure_ascii=False),
                "parent_table": foreign_key["parent"],
                "parent_fields_json": json.dumps(foreign_key["parent_fields"], ensure_ascii=False),
                "child_row_count": child_count,
                "foreign_key_violation_count": 0,
                "validation_status": "empirically_validated",
                "status_note": "Exact values and paired identifiers were checked; source-field semantics remain documented separately.",
            })
        connection.close()
        connection = None
        os.replace(temporary_path, output_path)
    except Exception:
        if connection is not None:
            connection.close()
        temporary_path.unlink(missing_ok=True)
        raise
    return output_path, table_results, relationship_results


def write_relational_database_reports(
    project_root: Path,
    table_results: list[dict[str, Any]],
    relationship_results: list[dict[str, Any]],
) -> tuple[Path, Path]:
    """Write aggregate SQLite verification reports under the data dictionary."""
    output_dir = Path(project_root) / "docs/data_dictionary"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / TABLE_REPORT_NAME, output_dir / RELATIONSHIP_REPORT_NAME]
    staged: list[Path] = []
    try:
        for destination, rows in zip(outputs, (table_results, relationship_results), strict=True):
            fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8-sig", newline="", dir=output_dir,
                prefix=f".{destination.name}.", suffix=".tmp", delete=False,
            ) as stream:
                staged_path = Path(stream.name)
                staged.append(staged_path)
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        for staged_path, destination in zip(staged, outputs, strict=True):
            os.replace(staged_path, destination)
    finally:
        for staged_path in staged:
            staged_path.unlink(missing_ok=True)
    return outputs[0], outputs[1]
