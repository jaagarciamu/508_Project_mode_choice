"""Profile relational EM2023 fields and candidate links for mode-choice data."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


DATABASE_RELATIVE_PATH = Path("data/relational/em2023_relational.sqlite")
DICTIONARY_RELATIVE_PATH = Path("docs/data_dictionary/mode_choice_trip_dataset_fields.csv")
TABLES = ("viajes", "personas", "hogares", "vehiculos", "etapas")
MAX_ENUMERATED_CATEGORIES = 50

PERSON_FIELD_PAIRS = {
    "edad": "edad", "sexo": "sexo", "genero": "genero", "orien_sexual": "orien_sexual",
    "identidad_etnica": "identidad_etnica", "madre_cab_familia": "madre_cab_familia",
    "max_nivel_edu": "max_nivel_edu", "ocupacion_principal": "ocupacion_principal",
}
HOUSEHOLD_FIELD_PAIRS = {
    "estra_hg": "estrato_hg", "nom_mun_hg": "nom_mpio_hg", "cod_upl_hg": "cod_upl_hg",
    "cod_utam_hg": "cod_utam_hg", "zat_hg": "zat_hg",
}


class ModeChoiceAuditError(RuntimeError):
    """Raised when the read-only mode-choice audit cannot complete safely."""


def _quote(value: str) -> str:
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
            writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="raise", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _columns(connection: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    return [(row[1], row[2] or "") for row in connection.execute(f"PRAGMA table_info({_quote(table)})")]


def _profile_field(connection: sqlite3.Connection, table: str, column: str, declared_type: str) -> dict[str, Any]:
    qtable, qcolumn = _quote(table), _quote(column)
    normalized_name = column.strip().casefold()
    code_like = normalized_name.startswith(("cod_", "key_")) or any(
        token in normalized_name for token in ("zat", "upl", "utam", "localidad", "municipio", "mun_")
    )
    numeric_test = "0" if code_like else (
        f"{qcolumn} IS NOT NULL AND trim(CAST({qcolumn} AS TEXT)) != '' "
        f"AND CAST({qcolumn} AS TEXT) NOT GLOB '*[^0-9eE+.-]*'"
    )
    total, nonnull, distinct, numeric, minimum, maximum, mean = connection.execute(
        f"SELECT COUNT(*), SUM(CASE WHEN {qcolumn} IS NOT NULL AND trim(CAST({qcolumn} AS TEXT))!='' THEN 1 ELSE 0 END), "
        f"COUNT(DISTINCT CASE WHEN {qcolumn} IS NOT NULL AND trim(CAST({qcolumn} AS TEXT))!='' THEN {qcolumn} END), "
        f"SUM(CASE WHEN {numeric_test} THEN 1 ELSE 0 END), "
        f"MIN(CASE WHEN {numeric_test} THEN CAST({qcolumn} AS REAL) END), "
        f"MAX(CASE WHEN {numeric_test} THEN CAST({qcolumn} AS REAL) END), "
        f"AVG(CASE WHEN {numeric_test} THEN CAST({qcolumn} AS REAL) END) FROM {qtable}"
    ).fetchone()
    values = None
    if distinct <= MAX_ENUMERATED_CATEGORIES:
        grouped = connection.execute(
            f"SELECT CAST({qcolumn} AS TEXT), COUNT(*) FROM {qtable} "
            f"WHERE {qcolumn} IS NOT NULL AND trim(CAST({qcolumn} AS TEXT))!='' "
            f"GROUP BY {qcolumn} ORDER BY COUNT(*) DESC, CAST({qcolumn} AS TEXT)"
        ).fetchall()
        values = json.dumps(
            [{"value": value, "count": count} for value, count in grouped],
            ensure_ascii=False, separators=(",", ":"),
        )
    return {
        "source_table": table, "source_field": column, "declared_type": declared_type,
        "rows_total": total, "rows_nonempty": nonnull, "rows_missing": total - nonnull,
        "distinct_nonnull_values": distinct, "numeric_parseable_values": numeric,
        "numeric_min": minimum, "numeric_max": maximum, "numeric_mean": mean,
        "observed_categories_json": values if values is not None else "",
        "category_summary": "enumerated_with_counts" if values is not None else "high_cardinality_summary_only",
    }


def audit_mode_choice_data(project_root: Path) -> dict[str, Any]:
    """Write aggregate relation/field reports and a field dictionary, reading SQLite only."""
    root = Path(project_root).resolve()
    database = root / DATABASE_RELATIVE_PATH
    if not database.is_file():
        raise ModeChoiceAuditError(f"Relational database not found: {DATABASE_RELATIVE_PATH.as_posix()}")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        table_names = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = set(TABLES).difference(table_names)
        if missing:
            raise ModeChoiceAuditError(f"Required relational tables are missing ({len(missing)})")
        columns = {table: _columns(connection, table) for table in TABLES}
        has = lambda table, column: column in {name for name, _ in columns[table]}

        counts = {table: connection.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0] for table in TABLES}
        quality_rows: list[dict[str, Any]] = []
        for table in TABLES:
            candidate_keys = {
                "viajes": ["key_viaje"], "personas": ["key_persona"],
                "hogares": ["key_hg"], "vehiculos": ["cod_vh"], "etapas": ["key_etapa"],
            }[table]
            for key in candidate_keys:
                if not has(table, key):
                    continue
                qtable, qkey = _quote(table), _quote(key)
                nulls = connection.execute(f"SELECT COUNT(*) FROM {qtable} WHERE {qkey} IS NULL OR trim(CAST({qkey} AS TEXT))='' ").fetchone()[0]
                duplicate_groups = connection.execute(
                    f"SELECT COUNT(*) FROM (SELECT {qkey} FROM {qtable} WHERE {qkey} IS NOT NULL GROUP BY {qkey} HAVING COUNT(*)>1)"
                ).fetchone()[0]
                quality_rows.append({"check": "key_profile", "table": table, "field": key,
                                     "value": counts[table], "status": "reported", "detail": f"missing={nulls}; duplicate_groups={duplicate_groups}"})

        def relation(name: str, left_table: str, left_key: str, right_table: str, right_key: str, one_to_one: bool) -> None:
            ql, qlk, qr, qrk = map(_quote, (left_table, left_key, right_table, right_key))
            missing_links = connection.execute(
                f"SELECT COUNT(*) FROM {ql} l LEFT JOIN {qr} r ON l.{qlk}=r.{qrk} WHERE r.{qrk} IS NULL"
            ).fetchone()[0]
            left_duplicate_groups = connection.execute(
                f"SELECT COUNT(*) FROM (SELECT {qlk} FROM {ql} WHERE {qlk} IS NOT NULL GROUP BY {qlk} HAVING COUNT(*)>1)"
            ).fetchone()[0]
            right_duplicate_groups = connection.execute(
                f"SELECT COUNT(*) FROM (SELECT {qrk} FROM {qr} WHERE {qrk} IS NOT NULL GROUP BY {qrk} HAVING COUNT(*)>1)"
            ).fetchone()[0]
            matched_rows = connection.execute(
                f"SELECT COUNT(*) FROM {ql} l JOIN {qr} r ON l.{qlk}=r.{qrk}"
            ).fetchone()[0]
            quality_rows.append({"check": "relationship", "table": name, "field": f"{left_table}.{left_key}->{right_table}.{right_key}",
                                 "value": matched_rows,
                                 "status": "validated" if not missing_links and not right_duplicate_groups and (not one_to_one or not left_duplicate_groups) else "review",
                                 "detail": f"left_rows={counts[left_table]}; unmatched_left_rows={missing_links}; left_repeated_key_groups={left_duplicate_groups}; right_duplicate_key_groups={right_duplicate_groups}; right_rows={counts[right_table]}"})

        relation("trip_person", "viajes", "key_pers", "personas", "key_persona", False)
        relation("trip_household", "viajes", "key_hg", "hogares", "key_hg", False)
        relation("stage_trip", "etapas", "key_viaje", "viajes", "key_viaje", False)
        relation("vehicle_household", "vehiculos", "key_hg", "hogares", "key_hg", False)

        # The alternate trip-person key is profiled explicitly and never used as a fallback.
        if has("viajes", "key_pers_viaja"):
            matches = connection.execute(
                'SELECT COUNT(*) FROM viajes v JOIN personas p ON v."key_pers_viaja"=p."key_persona"'
            ).fetchone()[0]
            quality_rows.append({"check": "alternate_link_diagnostic", "table": "viajes", "field": "key_pers_viaja->personas.key_persona",
                                 "value": matches, "status": "diagnostic_only", "detail": f"unmatched_trip_rows={counts['viajes'] - matches}; not used for enrichment"})

        stage_distribution = connection.execute(
            'SELECT stage_count, COUNT(*) FROM (SELECT v."key_viaje", COUNT(e."key_etapa") AS stage_count '
            'FROM viajes v LEFT JOIN etapas e ON v."key_viaje"=e."key_viaje" GROUP BY v."key_viaje") '
            'GROUP BY stage_count ORDER BY stage_count'
        ).fetchall()
        quality_rows.extend([
            {"check": "trips_without_stages", "table": "viajes", "field": "key_viaje->etapas", "value": sum(n for k, n in stage_distribution if k == 0), "status": "reported", "detail": "Trip count with zero linked stage records."},
            {"check": "trips_with_multiple_stages", "table": "viajes", "field": "key_viaje->etapas", "value": sum(n for k, n in stage_distribution if k > 1), "status": "reported", "detail": "Trip count with more than one linked stage record."},
        ])
        for stage_count, trip_count in stage_distribution:
            quality_rows.append({"check": "stage_count_distribution", "table": "viajes", "field": "stages_per_trip", "value": trip_count,
                                 "status": "reported", "detail": f"stage_count={stage_count}"})

        # Compare duplicated attributes without choosing a winning source.
        comparisons: list[dict[str, Any]] = []
        for trip_field, person_field in PERSON_FIELD_PAIRS.items():
            if not has("viajes", trip_field) or not has("personas", person_field):
                continue
            mismatches = connection.execute(
                f"SELECT COUNT(*) FROM viajes v JOIN personas p ON v.{_quote('key_pers')}=p.{_quote('key_persona')} "
                f"WHERE v.{_quote(trip_field)} IS NOT p.{_quote(person_field)}"
            ).fetchone()[0]
            comparisons.append({"comparison": "trip_vs_person", "trip_field": trip_field, "related_field": person_field,
                                "matched_rows": counts["viajes"], "mismatch_rows": mismatches,
                                "status": "same_values" if not mismatches else "documented_difference"})
        for trip_field, household_field in HOUSEHOLD_FIELD_PAIRS.items():
            if not has("viajes", trip_field) or not has("hogares", household_field):
                continue
            mismatches = connection.execute(
                f"SELECT COUNT(*) FROM viajes v JOIN hogares h ON v.{_quote('key_hg')}=h.{_quote('key_hg')} "
                f"WHERE v.{_quote(trip_field)} IS NOT h.{_quote(household_field)}"
            ).fetchone()[0]
            comparisons.append({"comparison": "trip_vs_household", "trip_field": trip_field, "related_field": household_field,
                                "matched_rows": counts["viajes"], "mismatch_rows": mismatches,
                                "status": "same_values" if not mismatches else "documented_difference"})

        profiles = [_profile_field(connection, table, name, declared_type) for table in TABLES for name, declared_type in columns[table]]
        dictionary_rows = []
        for profile in profiles:
            dictionary_rows.append({
                "source_table": profile["source_table"], "source_field": profile["source_field"],
                "declared_type": profile["declared_type"], "documented_definition": "",
                "definition_status": "pending_source_definition_review",
                "observed_categories_json": profile["observed_categories_json"],
                "category_summary": profile["category_summary"],
                "rows_total": profile["rows_total"], "rows_nonempty": profile["rows_nonempty"],
                "rows_missing": profile["rows_missing"], "distinct_nonnull_values": profile["distinct_nonnull_values"],
                "numeric_parseable_values": profile["numeric_parseable_values"],
                "numeric_min": profile["numeric_min"], "numeric_max": profile["numeric_max"], "numeric_mean": profile["numeric_mean"],
                "candidate_use": "source_field_for_review; no model inclusion decision",
                "candidate_transformation": "preserve_source_value; no aggregation in audit",
                "limitations": "Observed values are empirical; definition and model suitability require documentation/review.",
            })

        output_paths = {
            "quality": root / "outputs/tables/mode_choice_relation_audit.csv",
            "profiles": root / "outputs/tables/mode_choice_field_profile.csv",
            "comparisons": root / "outputs/tables/mode_choice_duplicate_field_comparison.csv",
            "dictionary": root / DICTIONARY_RELATIVE_PATH,
            "report": root / "outputs/reports/mode_choice_data_audit.md",
        }
        _atomic_csv(output_paths["quality"], ["check", "table", "field", "value", "status", "detail"], quality_rows)
        _atomic_csv(output_paths["profiles"], list(profiles[0]), profiles)
        _atomic_csv(output_paths["comparisons"], ["comparison", "trip_field", "related_field", "matched_rows", "mismatch_rows", "status"], comparisons)
        _atomic_csv(output_paths["dictionary"], list(dictionary_rows[0]), dictionary_rows)

        key_link = next(row for row in quality_rows if row["check"] == "relationship" and row["table"] == "trip_person")
        household_link = next(row for row in quality_rows if row["check"] == "relationship" and row["table"] == "trip_household")
        missing_stages = next(row["value"] for row in quality_rows if row["check"] == "trips_without_stages")
        multi_stages = next(row["value"] for row in quality_rows if row["check"] == "trips_with_multiple_stages")
        text = f"""# Auditoría de datos para elección modal

## Alcance

Auditoría descriptiva de la SQLite relacional local en modo solo lectura. La unidad candidata para una futura base analítica es el viaje (`viajes`); esta etapa no construye esa base, no decide inclusión final de variables y no estima modelos. Los campos fuente se conservan sin recodificación. Las definiciones no encontradas en la documentación disponible quedan pendientes, no se infieren a partir del nombre.

## Tamaño y relaciones candidatas

Conteos observados: {', '.join(f'`{table}` {counts[table]:,}' for table in TABLES)}.

El enlace candidato viaje–persona por `viajes.key_pers = personas.key_persona` empareja {key_link['value']:,} filas de viaje; {key_link['detail']}. El enlace viaje–hogar por `key_hg` empareja {household_link['value']:,}; {household_link['detail']}. La clave alternativa `key_pers_viaja` se reporta solo como diagnóstico y no se usa como fallback.

Hay {missing_stages:,} viajes sin registro de etapa y {multi_stages:,} viajes con más de una etapa. Por tanto, los campos de etapa no deben unirse directamente sin agregación: eso multiplicaría viajes. Costos, pagos, tiempos y modos por etapa se perfilan a nivel de tabla etapa, pero esta auditoría no los suma al viaje.

## Perfil de campos y discrepancias

El diccionario `docs/data_dictionary/mode_choice_trip_dataset_fields.csv` contiene una fila por campo de las cinco tablas: tipo declarado, cobertura, valores categóricos con frecuencia cuando la cardinalidad es baja, estadísticas numéricas, definición documentada (si está disponible) y uso/transformación candidatos aún no aprobados. Para campos con más de {MAX_ENUMERATED_CATEGORIES} valores distintos no se enumeran los valores individuales; se reportan cardinalidad, faltantes y rango/resumen numérico cuando aplica.

Las comparaciones de atributos repetidos entre viaje, persona y hogar se encuentran en `outputs/tables/mode_choice_duplicate_field_comparison.csv`. Las diferencias son conteos de registros no coincidentes; no seleccionan una tabla como verdad ni cambian datos.

## Productos y siguiente paso

Los reportes agregados son `outputs/tables/mode_choice_relation_audit.csv`, `mode_choice_field_profile.csv` y `mode_choice_duplicate_field_comparison.csv`. No contienen identificadores ni filas de microdatos. La siguiente fase, después de revisar estos resultados, puede especificar y construir una base de una fila por viaje, definiendo de forma explícita cómo agregar atributos de hogar, vehículos y etapas. No se asume que estén disponibles atributos de alternativas no elegidas; por ello, el modo observado permite empezar con análisis descriptivo/asociativo, pero no basta por sí solo para establecer una comparación completa entre opciones.
"""
        output_paths["report"].parent.mkdir(parents=True, exist_ok=True)
        output_paths["report"].write_text(text, encoding="utf-8")
        return {"table_counts": counts, "profile_rows": len(profiles), "dictionary_rows": len(dictionary_rows),
                "relationship_checks": sum(r["check"] == "relationship" for r in quality_rows),
                "trip_person_matches": key_link["value"], "trip_household_matches": household_link["value"],
                "trips_without_stages": missing_stages, "trips_with_multiple_stages": multi_stages,
                "outputs": {name: path.relative_to(root).as_posix() for name, path in output_paths.items()}}
    except ModeChoiceAuditError:
        raise
    except Exception as exc:
        raise ModeChoiceAuditError(f"Could not complete mode-choice data audit ({type(exc).__name__})") from exc
    finally:
        if connection is not None:
            connection.close()
