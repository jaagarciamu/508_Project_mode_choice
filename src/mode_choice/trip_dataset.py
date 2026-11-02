"""Build the first source-faithful, trip-level analytical dataset."""

from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


DATABASE_RELATIVE_PATH = Path("data/relational/em2023_relational.sqlite")
DATASET_RELATIVE_PATH = Path("data/analytical/em2023_trip_dataset.csv")
SCHEMA_REPORT_RELATIVE_PATH = Path("docs/data_dictionary/analytical_trip_dataset_fields.csv")

TRIP_KEY = "key_viaje"
FIELD_GROUPS: dict[str, set[str]] = {
    "record_identifiers": {"key_viaje", "cod_vj", "cod_pers", "key_pers", "key_pers_viaja", "cod_hg", "key_hg"},
    "origin_destination": {"zat_ori", "utam_ori", "upl_ori", "localidad_ori", "nom_mun_ori", "zat_des", "utam_des", "upl_des", "localidad_des", "nom_mun_des"},
    "time_and_duration": {" hora_ini ", "hora_fin", " duracion_min ", "t_acceso_min", "t_espera_min", "t_egreso_min"},
    "mode_and_trip_purpose": {"modo_principal_agrupado", "modo_principal_desagrupado", "motivo_viaje", "motivo_viaje_cuidado", "frecuencia_viaje", "etapas"},
    "person_and_household_attributes": {"edad", "sexo", "genero", "orien_sexual", "identidad_etnica", "madre_cab_familia", "max_nivel_edu", "ocupacion_principal", "estra_hg", "nom_mun_hg", "cod_upl_hg", "cod_utam_hg", "zat_hg"},
    "expansion_weight_unapplied": {"fexp_vj"},
}


class TripDatasetError(RuntimeError):
    """Raised when the validated trip dataset cannot be built safely."""


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _atomic_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            staged = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def build_trip_dataset(project_root: Path) -> tuple[Path, Path, dict[str, int]]:
    """Create an unweighted CSV with one row per SQLite trip and exact source fields."""
    project_root = Path(project_root).resolve()
    database_path = project_root / DATABASE_RELATIVE_PATH
    output_path = project_root / DATASET_RELATIVE_PATH
    schema_path = project_root / SCHEMA_REPORT_RELATIVE_PATH
    if not database_path.is_file():
        raise TripDatasetError(f"Relational database not found: {DATABASE_RELATIVE_PATH.as_posix()}")

    connection: sqlite3.Connection | None = None
    staged: Path | None = None
    try:
        connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
        source_columns = [row[1] for row in connection.execute('PRAGMA table_info("viajes")')]
        if not source_columns or TRIP_KEY not in source_columns:
            raise TripDatasetError("The viajes table is missing or does not contain its validated trip key")
        for group_fields in FIELD_GROUPS.values():
            unknown = group_fields.difference(source_columns)
            if unknown:
                raise TripDatasetError(f"Expected source fields are missing from viajes ({len(unknown)} fields)")

        table_count = connection.execute('SELECT COUNT(*) FROM "viajes"').fetchone()[0]
        distinct_keys = connection.execute(
            f'SELECT COUNT(DISTINCT {_quote_identifier(TRIP_KEY)}) FROM "viajes"'
        ).fetchone()[0]
        null_keys = connection.execute(
            f'SELECT COUNT(*) FROM "viajes" WHERE {_quote_identifier(TRIP_KEY)} IS NULL'
        ).fetchone()[0]
        if table_count != distinct_keys or null_keys:
            raise TripDatasetError("The validated trip key is not unique and non-null in viajes")

        selected = ", ".join(_quote_identifier(name) for name in source_columns)
        query = f'SELECT {selected} FROM "viajes" ORDER BY rowid'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            staged = Path(stream.name)
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(source_columns)
            for row in connection.execute(query):
                writer.writerow(row)

        # Re-read the staged artifact before publication to verify exact row and field counts.
        with staged.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            output_headers = next(reader, None)
            output_rows = sum(1 for _ in reader)
        if output_headers != source_columns or output_rows != table_count:
            raise TripDatasetError("Staged trip dataset failed header or row-count validation")

        schema_rows = []
        grouped_fields = {field: group for group, fields in FIELD_GROUPS.items() for field in fields}
        for position, name in enumerate(source_columns, start=1):
            schema_rows.append({
                "position": position,
                "source_column": name,
                "provisional_analytical_role": grouped_fields.get(name, "other_source_trip_field"),
                "source_table": "viajes",
                "transformation": "preserved_as_stored_text",
                "weighting_status": "retained_not_applied" if name == "fexp_vj" else "not_applicable",
                "definition_status": "pending_documentation_review",
            })

        # Publish the data only after all database and staged-output checks pass.
        os.replace(staged, output_path)
        staged = None
        _atomic_csv(schema_path, list(schema_rows[0]), schema_rows)
        summary = {
            "source_trip_rows": table_count,
            "dataset_rows": output_rows,
            "source_columns": len(source_columns),
            "dataset_columns": len(output_headers),
            "distinct_trip_keys": distinct_keys,
            "null_trip_keys": null_keys,
        }
        return output_path, schema_path, summary
    except TripDatasetError:
        raise
    except Exception as exc:
        raise TripDatasetError(f"Could not build the analytical trip dataset ({type(exc).__name__})") from exc
    finally:
        if connection is not None:
            connection.close()
        if staged is not None:
            staged.unlink(missing_ok=True)
