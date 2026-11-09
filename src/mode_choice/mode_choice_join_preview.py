"""Build a small, local-only preview of a one-row-per-trip enriched join."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

DATABASE_RELATIVE_PATH = Path("data/relational/em2023_relational.sqlite")
PREVIEW_RELATIVE_PATH = Path("data/interim/mode_choice_trip_join_preview.csv")
ROWS_PER_MODE = 3
TABLES = ("viajes", "personas", "hogares")


class JoinPreviewError(RuntimeError):
    """Raised when the sample join cannot be built without multiplying trips."""


def _q(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({_q(table)})")]


def _atomic_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            staged = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="raise", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def build_join_preview(project_root: Path, rows_per_mode: int = ROWS_PER_MODE) -> tuple[Path, dict[str, Any]]:
    """Join up to N example trips per observed mode with person/household and child summaries."""
    root = Path(project_root).resolve()
    database = root / DATABASE_RELATIVE_PATH
    output = root / PREVIEW_RELATIVE_PATH
    if not database.is_file():
        raise JoinPreviewError(f"Relational database not found: {DATABASE_RELATIVE_PATH.as_posix()}")
    if rows_per_mode < 1:
        raise JoinPreviewError("rows_per_mode must be positive")

    connection: sqlite3.Connection | None = None
    staged: Path | None = None
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        trip_fields = _table_columns(connection, "viajes")
        person_fields = _table_columns(connection, "personas")
        household_fields = _table_columns(connection, "hogares")

        trip_select = [f"v.{_q(field)} AS {_q(field)}" for field in trip_fields]
        person_select = [f"p.{_q(field)} AS {_q('persona__' + field)}" for field in person_fields]
        household_select = [f"h.{_q(field)} AS {_q('hogar__' + field)}" for field in household_fields]

        stage_summary = '''
            SELECT key_viaje, COUNT(*) AS stage_count,
                   group_concat(modo_etapa, ' | ') AS stage_mode_sequence,
                   SUM(CASE WHEN trim(CAST(t_acceso_min AS TEXT)) GLOB '[0-9]*' THEN CAST(t_acceso_min AS REAL) END) AS stage_access_minutes_sum_exploratory,
                   SUM(CASE WHEN trim(CAST(t_espera_min AS TEXT)) GLOB '[0-9]*' THEN CAST(t_espera_min AS REAL) END) AS stage_wait_minutes_sum_exploratory,
                   SUM(CASE WHEN trim(CAST(t_egreso_min AS TEXT)) GLOB '[0-9]*' THEN CAST(t_egreso_min AS REAL) END) AS stage_egress_minutes_sum_exploratory,
                   SUM(CASE WHEN trim(CAST(costo_viaje AS TEXT)) GLOB '[0-9]*' THEN CAST(costo_viaje AS REAL) END) AS stage_cost_sum_exploratory,
                   SUM(CASE WHEN trim(CAST(pago_viaje AS TEXT)) GLOB '[0-9]*' THEN CAST(pago_viaje AS REAL) END) AS stage_payment_sum_exploratory,
                   SUM(CASE WHEN trim(CAST(costo_parqueo AS TEXT)) GLOB '[0-9]*' THEN CAST(costo_parqueo AS REAL) END) AS stage_parking_cost_sum_exploratory
            FROM (SELECT * FROM etapas ORDER BY key_viaje, orden_eta)
            GROUP BY key_viaje
        '''
        vehicle_summary = '''
            SELECT key_hg, COUNT(*) AS vehicle_records_in_household,
                   SUM(CASE WHEN trim(CAST(cantidad AS TEXT)) GLOB '[0-9]*' THEN CAST(cantidad AS REAL) END) AS vehicle_quantity_sum_exploratory,
                   group_concat("tipo_vehículo", ' | ') AS vehicle_type_values
            FROM vehiculos GROUP BY key_hg
        '''
        extras = [
            "s.stage_count", "s.stage_mode_sequence", "s.stage_access_minutes_sum_exploratory",
            "s.stage_wait_minutes_sum_exploratory", "s.stage_egress_minutes_sum_exploratory",
            "s.stage_cost_sum_exploratory", "s.stage_payment_sum_exploratory", "s.stage_parking_cost_sum_exploratory",
            "COALESCE(vh.vehicle_records_in_household, 0) AS vehicle_records_in_household",
            "vh.vehicle_quantity_sum_exploratory", "vh.vehicle_type_values",
        ]
        query = f'''
            WITH chosen_trips AS (
                SELECT key_viaje, ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(modo_principal_agrupado, '<NULL>') ORDER BY rowid
                ) AS mode_sample_rank
                FROM viajes
            ), stage_summary AS ({stage_summary}), vehicle_summary AS ({vehicle_summary})
            SELECT {', '.join(trip_select + person_select + household_select + extras)}
            FROM chosen_trips c
            JOIN viajes v ON v.key_viaje=c.key_viaje
            LEFT JOIN personas p ON v.key_pers=p.key_persona
            LEFT JOIN hogares h ON v.key_hg=h.key_hg
            LEFT JOIN stage_summary s ON s.key_viaje=v.key_viaje
            LEFT JOIN vehicle_summary vh ON vh.key_hg=v.key_hg
            WHERE c.mode_sample_rank <= ?
            ORDER BY v.modo_principal_agrupado, c.mode_sample_rank, v.rowid
        '''
        rows = [dict(row) for row in connection.execute(query, (rows_per_mode,))]
        headers = list(rows[0]) if rows else []
        if len({row.get("key_viaje") for row in rows}) != len(rows):
            raise JoinPreviewError("Preview join multiplied trips; refusing to write the sample")
        if any(row.get("persona__key_persona") is None or row.get("hogar__key_hg") is None for row in rows):
            raise JoinPreviewError("Preview contains an unmatched person or household")

        counts = connection.execute(
            'SELECT COALESCE(modo_principal_agrupado, \'<NULL>\'), COUNT(*) FROM viajes GROUP BY modo_principal_agrupado ORDER BY 1'
        ).fetchall()
        _atomic_csv(output, headers, rows)
        summary = {
            "preview_rows": len(rows), "rows_per_mode": rows_per_mode,
            "observed_modes": len(counts),
            "source_trips": connection.execute("SELECT COUNT(*) FROM viajes").fetchone()[0],
            "all_rows_have_one_trip_person_household": True,
            "row_count_is_illustrative_not_statistically_representative": True,
            "mode_counts": [{"mode": mode, "source_trip_count": count} for mode, count in counts],
            "output": output.relative_to(root).as_posix(),
            "aggregation_note": "Stage and vehicle values are exploratory summaries only; no aggregation rule is approved for the final model dataset.",
        }
        notes = output.with_suffix(".README.md")
        notes.write_text(
            "# Muestra local de unión para elección modal\n\n"
            "Archivo de revisión local, derivado de la SQLite existente y excluido de Git. Contiene un máximo de "
            f"{rows_per_mode} viajes de ejemplo por categoría observada de modo, no una muestra estadística. Incluye campos originales de viaje, persona y hogar con prefijos para distinguir su procedencia. "
            "Vehículos y etapas se resumen para conservar una fila por viaje. Las columnas con sufijo `_exploratory` y las secuencias de categorías son únicamente ilustrativas; no constituyen reglas aprobadas de agregación ni valores listos para modelar. "
            "El archivo contiene microdatos e identificadores y debe permanecer local, fuera de Git.\n",
            encoding="utf-8",
        )
        return output, summary
    except JoinPreviewError:
        raise
    except Exception as exc:
        raise JoinPreviewError(f"Could not build trip join preview ({type(exc).__name__})") from exc
    finally:
        if connection is not None:
            connection.close()
        if staged is not None:
            staged.unlink(missing_ok=True)
