"""Build a small, local-only preview of a one-row-per-trip enriched join."""

from __future__ import annotations

import csv
import os
import random
import sqlite3
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DATABASE_RELATIVE_PATH = Path("data/relational/em2023_relational.sqlite")
DISTANCE_RELATIVE_PATH = Path("data/sources/raw/zonification/ZAT_Distance.csv")
PREVIEW_RELATIVE_PATH = Path("data/interim/mode_choice_trip_join_preview_350.csv")
SAMPLE_SIZE = 350
SAMPLE_SEED = 5082026


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


def _canonical_zone(value: Any, field: str) -> int | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    if "," in text:
        text = text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise JoinPreviewError(f"Non-numeric zone code in {field}") from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise JoinPreviewError(f"Non-integral or non-finite zone code in {field}")
    return int(number)


def _allocate_sample(mode_counts: dict[Any, int], sample_size: int) -> dict[Any, int]:
    total = sum(mode_counts.values())
    if sample_size < len(mode_counts) or sample_size > total:
        raise JoinPreviewError("Sample size must cover every observed mode and cannot exceed trip count")
    allocation = {mode: 1 for mode in mode_counts}
    remaining = sample_size - len(mode_counts)
    if remaining:
        exact = {mode: remaining * count / total for mode, count in mode_counts.items()}
        additions = {mode: int(value) for mode, value in exact.items()}
        for mode, count in additions.items():
            allocation[mode] += count
        remainder = sample_size - sum(allocation.values())
        order = sorted(mode_counts, key=lambda mode: (-(exact[mode] - additions[mode]), "" if mode is None else str(mode)))
        for mode in order[:remainder]:
            allocation[mode] += 1
    if any(allocation[mode] > mode_counts[mode] for mode in mode_counts):
        raise JoinPreviewError("Sample allocation exceeds a source mode stratum")
    return allocation


def _read_distance_table(path: Path, needed_pairs: set[tuple[int, int]]) -> tuple[dict[tuple[int, int], Decimal], dict[str, int]]:
    if not path.is_file():
        raise JoinPreviewError(f"ZAT distance table not found: {DISTANCE_RELATIVE_PATH.as_posix()}")
    seen_pairs: set[tuple[int, int]] = set()
    distance_lookup: dict[tuple[int, int], Decimal] = {}
    source_zones: set[int] = set()
    row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        expected = {"ZAT_ORI", "ZAT_DEST", "NEAR_DIST", "NEAR_RANK"}
        if not reader.fieldnames or not expected.issubset(reader.fieldnames):
            raise JoinPreviewError("ZAT distance table is missing required fields")
        for row in reader:
            row_count += 1
            origin = _canonical_zone(row["ZAT_ORI"], "ZAT_ORI")
            destination = _canonical_zone(row["ZAT_DEST"], "ZAT_DEST")
            if origin is None or destination is None:
                raise JoinPreviewError("ZAT distance table contains an empty zone code")
            pair = (origin, destination)
            if pair in seen_pairs:
                raise JoinPreviewError("Duplicate directed ZAT pair after strict numeric representation parsing")
            seen_pairs.add(pair)
            source_zones.update(pair)
            if origin == destination:
                raise JoinPreviewError("Distance table contains a diagonal pair; expected self-pairs to be omitted")
            try:
                distance = Decimal(row["NEAR_DIST"].strip().replace(",", "."))
                rank = int(row["NEAR_RANK"])
            except (InvalidOperation, ValueError) as exc:
                raise JoinPreviewError("Invalid distance or rank value in ZAT distance table") from exc
            if not distance.is_finite() or distance < 0 or rank < 1:
                raise JoinPreviewError("Distance must be finite/nonnegative and rank must be positive")
            if pair in needed_pairs:
                distance_lookup[pair] = distance
    return distance_lookup, {"row_count": row_count, "unique_directed_pairs": len(seen_pairs), "zone_count": len(source_zones)}


def build_join_preview(
    project_root: Path, sample_size: int = SAMPLE_SIZE, random_seed: int = SAMPLE_SEED,
) -> tuple[Path, dict[str, Any]]:
    """Build a stratified, local-only trip preview with validated centroid distances."""
    root = Path(project_root).resolve()
    database = root / DATABASE_RELATIVE_PATH
    output = root / PREVIEW_RELATIVE_PATH
    if not database.is_file():
        raise JoinPreviewError(f"Relational database not found: {DATABASE_RELATIVE_PATH.as_posix()}")
    if sample_size < 1:
        raise JoinPreviewError("sample_size must be positive")

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

        mode_counts = {
            mode: count for mode, count in connection.execute(
                'SELECT modo_principal_agrupado, COUNT(*) FROM viajes GROUP BY modo_principal_agrupado'
            ).fetchall()
        }
        allocation = _allocate_sample(mode_counts, sample_size)
        rng = random.Random(random_seed)
        selected_rowids: list[int] = []
        for mode in sorted(mode_counts, key=lambda item: "" if item is None else str(item)):
            rowids = [row[0] for row in connection.execute(
                'SELECT rowid FROM viajes WHERE modo_principal_agrupado IS ? ORDER BY rowid', (mode,)
            )]
            selected_rowids.extend(rng.sample(rowids, allocation[mode]))

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
        placeholders = ",".join("?" for _ in selected_rowids)
        query = f'''
            WITH stage_summary AS ({stage_summary}), vehicle_summary AS ({vehicle_summary})
            SELECT {', '.join(trip_select + person_select + household_select + extras)}
            FROM viajes v
            LEFT JOIN personas p ON v.key_pers=p.key_persona
            LEFT JOIN hogares h ON v.key_hg=h.key_hg
            LEFT JOIN stage_summary s ON s.key_viaje=v.key_viaje
            LEFT JOIN vehicle_summary vh ON vh.key_hg=v.key_hg
            WHERE v.rowid IN ({placeholders})
            ORDER BY v.modo_principal_agrupado, v.rowid
        '''
        rows = [dict(row) for row in connection.execute(query, selected_rowids)]
        headers = list(rows[0]) if rows else []
        if len(rows) != sample_size:
            raise JoinPreviewError(f"Expected {sample_size} preview trips; found {len(rows)}")
        if len({row.get("key_viaje") for row in rows}) != len(rows):
            raise JoinPreviewError("Preview join multiplied trips; refusing to write the sample")
        if any(row.get("persona__key_persona") is None or row.get("hogar__key_hg") is None for row in rows):
            raise JoinPreviewError("Preview contains an unmatched person or household")

        needed_pairs: set[tuple[int, int]] = set()
        for row in rows:
            origin = _canonical_zone(row.get("zat_ori"), "viajes.zat_ori")
            destination = _canonical_zone(row.get("zat_des"), "viajes.zat_des")
            if origin is not None and destination is not None and origin != destination:
                needed_pairs.add((origin, destination))
        distance_lookup, distance_source = _read_distance_table(root / DISTANCE_RELATIVE_PATH, needed_pairs)
        distance_status_counts: dict[str, int] = {}
        for row in rows:
            origin = _canonical_zone(row.get("zat_ori"), "viajes.zat_ori")
            destination = _canonical_zone(row.get("zat_des"), "viajes.zat_des")
            if origin is None or destination is None:
                row["zat_centroid_distance_m"] = ""
                row["zat_distance_status"] = "missing_zone_code"
            elif origin == destination:
                row["zat_centroid_distance_m"] = Decimal("0")
                row["zat_distance_status"] = "intrazonal_zero_derived"
            elif (origin, destination) in distance_lookup:
                row["zat_centroid_distance_m"] = distance_lookup[(origin, destination)]
                row["zat_distance_status"] = "matched_pair"
            else:
                row["zat_centroid_distance_m"] = ""
                row["zat_distance_status"] = "unmatched_zone_pair"
            status = row["zat_distance_status"]
            distance_status_counts[status] = distance_status_counts.get(status, 0) + 1
        headers.extend(["zat_centroid_distance_m", "zat_distance_status"])
        _atomic_csv(output, headers, rows)
        sample_mode_counts: dict[str, int] = {}
        for row in rows:
            label = "<NULL>" if row.get("modo_principal_agrupado") is None else str(row["modo_principal_agrupado"])
            sample_mode_counts[label] = sample_mode_counts.get(label, 0) + 1
        summary = {
            "preview_rows": len(rows), "sample_size": sample_size, "random_seed": random_seed,
            "source_mode_strata": len(mode_counts), "sample_mode_counts": sample_mode_counts,
            "source_mode_allocation": {"<NULL>" if key is None else str(key): value for key, value in allocation.items()},
            "source_trips": connection.execute("SELECT COUNT(*) FROM viajes").fetchone()[0],
            "all_rows_have_one_trip_person_household": True,
            "sample_is_stratified_and_not_for_inference": True,
            "distance_source": DISTANCE_RELATIVE_PATH.as_posix(), "distance_table_validation": distance_source,
            "distance_status_counts": distance_status_counts,
            "output": output.relative_to(root).as_posix(),
            "aggregation_note": "Stage and vehicle values are exploratory summaries only; no aggregation rule is approved for the final model dataset.",
        }
        notes = output.with_suffix(".README.md")
        notes.write_text(
            "# Muestra local de unión para elección modal\n\n"
            "Archivo de revisión local, derivado de la SQLite existente y excluido de Git. Contiene un máximo de "
            f"{sample_size} viajes en total, asignados proporcionalmente por modo con semilla fija {random_seed}, garantizando al menos un viaje por modo. La muestra es para revisión, no para inferencia. Incluye campos originales de viaje, persona y hogar con prefijos para distinguir su procedencia. "
            "Vehículos y etapas se resumen para conservar una fila por viaje. Las columnas con sufijo `_exploratory` y las secuencias de categorías son únicamente ilustrativas; no constituyen reglas aprobadas de agregación ni valores listos para modelar. "
            "`zat_centroid_distance_m` se empata por el par dirigido de ZAT tras validar que los códigos decimales del CSV representan enteros; conserva los códigos de viaje originales. Los intrazonales reciben 0 derivado (`intrazonal_zero_derived`) porque la tabla fuente omite diagonales. Las distancias emparejadas proceden de `NEAR_DIST` en metros. "
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
