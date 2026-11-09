"""Build daily EODH OD matrices without changing source zone identifiers."""

from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


DATABASE = Path("data/relational/em2023_relational.sqlite")
SAMPLE_CSV = Path("outputs/matrices/od_daily_sample.csv")
SAMPLE_PARQUET = Path("outputs/matrices/od_daily_sample.parquet")
EXPANDED_CSV = Path("outputs/matrices/od_daily_expanded.csv")
EXPANDED_PARQUET = Path("outputs/matrices/od_daily_expanded.parquet")
RECONCILIATION_CSV = Path("outputs/tables/od_reconciliation.csv")
QUALITY_CSV = Path("outputs/tables/od_data_quality.csv")
ZONE_SUMMARY_CSV = Path("outputs/tables/od_zone_summary.csv")
METHODOLOGY_MD = Path("outputs/reports/od_matrix_methodology.md")
BENCHMARK = Decimal("16723044")
LEGACY_INTERNAL_TRIP_COUNT = 99741
LEGACY_INTERNAL_INTRAZONAL_COUNT = 15013
# Historical comparison counts from the superseded internal-only release.


class ODMatrixError(RuntimeError):
    """Raised when an auditable OD product cannot be built safely."""


def _source_zone(value: Any) -> str | None:
    """Return a nonblank source identifier verbatim, without normalizing it."""
    if value is None:
        return None
    raw = str(value)
    return None if not raw.strip() else raw


def _parse_factor(value: Any) -> Decimal | None:
    """Parse source weights while accepting the survey's decimal-comma format."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        if "," in raw:
            # Source values may use periods as thousands separators and comma decimals.
            raw = raw.replace(".", "").replace(",", ".")
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if value is None else str(value) for key, value in row.items()})


def _decimal_arrow_type(values: list[Decimal | None]) -> pa.DataType:
    scales = [max(0, -value.as_tuple().exponent) for value in values if value is not None]
    scale = max(scales, default=2)
    integer_digits = max(
        (max(1, len(value.as_tuple().digits) + value.as_tuple().exponent) for value in values if value is not None),
        default=1,
    )
    precision = max(20, integer_digits + scale + 2)
    if precision > 38:
        raise ODMatrixError("Expanded values exceed Parquet decimal128 precision")
    return pa.decimal128(precision, scale)


def _write_parquet(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    decimals = [row.get("expanded_trips") for row in rows]
    schema = pa.schema([
        pa.field("zat_ori", pa.string(), nullable=False),
        pa.field("zat_des", pa.string(), nullable=False),
        pa.field(fields[2], _decimal_arrow_type(decimals) if fields[2] == "expanded_trips" else pa.int64(), nullable=fields[2] == "expanded_trips"),
        *(
            [pa.field("sample_trips", pa.int64(), nullable=False),
             pa.field("weighted_trip_records", pa.int64(), nullable=False),
             pa.field("invalid_weight_records", pa.int64(), nullable=False)]
            if fields[2] == "expanded_trips" else []
        ),
    ])
    arrays = [pa.array([row[field] for row in rows], type=schema.field(field).type) for field in fields]
    pq.write_table(pa.Table.from_arrays(arrays, schema=schema), path, compression="zstd")


def _metric(name: str, value: Any, status: str = "reported", detail: str = "") -> dict[str, Any]:
    return {"metric": name, "value": value, "status": status, "detail": detail}


def _format_spanish(value: Decimal) -> str:
    return format(value, ",f").replace(",", "§").replace(".", ",").replace("§", ".")


def _write_methodology(path: Path, summary: dict[str, Any], factor_stats: dict[str, dict[str, Any]]) -> None:
    fexp_hg = factor_stats["fexp_hg"]
    fexp_vj = factor_stats["fexp_vj"]
    comparison = _format_spanish(summary["benchmark_difference"]) if summary["benchmark_difference"] is not None else "no disponible"
    percent = _format_spanish(summary["benchmark_difference_percent"]) if summary["benchmark_difference_percent"] is not None else "no disponible"
    coverage = "completa" if summary["invalid_weight_records"] == 0 else "incompleta"
    factor_positive_count = fexp_hg["numeric_count"] - fexp_hg["zero_count"] - fexp_hg["negative_count"]
    text = f"""# Matrices diarias OD EODH — metodología y limitaciones

## Productos y fuente

Las matrices son productos descriptivos del archivo local `data/relational/em2023_relational.sqlite`, usando las tablas `viajes` y `hogares`. La base se abre en modo de solo lectura. La tabla de viajes conserva {summary['source_trip_rows']:,} registros y la clave `key_viaje` es única y no nula.

Se incluyen todos los registros con códigos de origen y destino no vacíos, sin filtros por propósito, modo, edad, tiempo u otras características. Los identificadores de zona se conservan como texto exactamente como están almacenados. Los códigos vacíos se contabilizan en QA y no forman una celda OD. Se retienen los intrazonales y todos los pares observados, incluso cuando el código no tenga una correspondencia geográfica validada.

El CSV y Parquet se publican en formato disperso largo: una fila por par observado, columnas `zat_ori`, `zat_des` y conteo o expansión. Los pares de la matriz expandida siguen la misma lista que la matriz muestral. Cuando algún viaje del par carezca de un factor válido, la expansión de esa celda queda vacía y se informa su cobertura; no se representa como cero.

## Regla de expansión

El informe P6 de Etapa IV describe el total de viajes mediante la suma por hogar del factor de expansión del hogar multiplicado por el número de viajes reportados por ese hogar. Se aplica la forma equivalente de repetir `fexp_hg` en cada viaje asociado: suma de factores de hogar por registro de viaje. Es una reconstrucción técnica basada en la fórmula documentada, no una reproducción exacta de los scripts contractuales.

En los datos actuales, `fexp_hg` es numérico en {fexp_hg['numeric_count']:,} viajes, de los cuales {factor_positive_count:,} tienen valor positivo; su suma repetida por viaje es {_format_spanish(fexp_hg['trip_sum'])}. El campo `fexp_vj` es numérico en {fexp_vj['numeric_count']:,} viajes, de los cuales {fexp_vj['numeric_count'] - fexp_vj['zero_count'] - fexp_vj['negative_count']:,} tienen valor positivo; su suma es {_format_spanish(fexp_vj['trip_sum'])}. `fexp_hg` varía dentro de {summary['variable_fexp_hg_households']:,} hogares con viajes y `fexp_vj` dentro de {summary['variable_fexp_vj_households']:,}; ambos factores difieren en {summary['factor_mismatch_records']:,} registros. `fexp_vj` se reporta como diagnóstico, no se usa como peso principal.

## Geografía y cobertura

No se asigna municipio, pertenencia al área de estudio ni equivalencia espacial a partir de una conversión inferida de códigos. En la revisión local, los identificadores fuente son texto y el campo ZAT del DBF de referencia se almacena como número decimal; no hay coincidencias de representación exacta. Por esa razón el DBF no se usa para filtrar ni para renombrar zonas. Los posibles códigos no emparejados quedan incluidos en las matrices y aparecen en el resumen por zona como sin clasificación geográfica validada.

El producto georreferenciado de Etapa IV reporta 56.240 registros frente a los 100.174 viajes de la base final. Se trata como diferencia descriptiva entre productos; no se usa como universo o filtro de las matrices. El informe de validación documenta 23.082 hogares encuestados, 22.755 válidos tras MIC, 187 incompletos y 140 anulados. Este pipeline usa la base final ya procesada y no intenta reconstruir el MIC.

La matriz histórica restringida al área de estudio contenía 99.741 viajes y 15.013 intrazonales. La matriz actual incorpora los 433 registros restantes con sus códigos originales y registra 15.016 intrazonales en el universo ampliado; los tres casos adicionales provienen de fuera de la matriz histórica restringida.

## Conciliación con el benchmark

El total expandido con cobertura de factor {coverage} es {_format_spanish(summary['expanded_total'])}. Frente al benchmark publicado de {_format_spanish(BENCHMARK)}, la diferencia es {comparison} ({percent}% del benchmark). Esta comparación es descriptiva: la proximidad no valida la equivalencia de factores, universos, geografía o procedimientos.

## Limitaciones

- No se reconstruyen las rutinas R contractuales citadas en el anexo del informe P6, que no están presentes entre los archivos locales catalogados.
- El campo `fexp_vj` no coincide registro a registro con `fexp_hg`; no se interpreta esa discrepancia como error ni se corrigen los valores.
- No se calculan errores estándar, intervalos de confianza o CV por celda. El CV publicado para el total no se aplica a las celdas OD.
- No se generan matrices por modo ni por período AM/PM, y no se usan factores EODI ni aforos.
- Diferencias en completitud, geografía o denominadores se documentan como limitaciones, sin forzar coincidencias con el producto publicado.

## Trazabilidad

La evidencia está en los informes P4, P5 y P6 de Etapa IV, el inventario de fuentes y `docs/decisions/decision_log.md`. Los productos agregados no incluyen identificadores de viaje, hogar o persona.
"""
    path.write_text(text, encoding="utf-8")


def build_od_products(project_root: Path) -> dict[str, Any]:
    """Build daily sample and household-factor OD matrices plus aggregate QA."""
    root = Path(project_root).resolve()
    db_path = root / DATABASE
    if not db_path.is_file():
        raise ODMatrixError(f"Required input not found: {DATABASE.as_posix()}")

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        table_names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"viajes", "hogares"}.issubset(table_names):
            raise ODMatrixError("The relational database must contain viajes and hogares tables")
        trip_columns = {row[1] for row in conn.execute('PRAGMA table_info("viajes")')}
        household_columns = {row[1] for row in conn.execute('PRAGMA table_info("hogares")')}
        required_trip = {"key_viaje", "key_hg", "zat_ori", "zat_des", "fexp_vj"}
        required_household = {"key_hg", "fexp_hg"}
        if not required_trip.issubset(trip_columns) or not required_household.issubset(household_columns):
            raise ODMatrixError("The relational tables lack required trip, household, zone, or factor fields")

        trip_count, distinct_keys, null_keys = conn.execute(
            'SELECT COUNT(*), COUNT(DISTINCT "key_viaje"), '
            'SUM("key_viaje" IS NULL) FROM "viajes"'
        ).fetchone()
        household_count, distinct_households, null_household_keys = conn.execute(
            'SELECT COUNT(*), COUNT(DISTINCT "key_hg"), SUM("key_hg" IS NULL) FROM "hogares"'
        ).fetchone()
        if trip_count != distinct_keys or null_keys:
            raise ODMatrixError("The trip key is not unique and non-null")
        if household_count != distinct_households or null_household_keys:
            raise ODMatrixError("The household key is not unique and non-null")

        query = '''
            SELECT t."key_viaje", t."key_hg", t."zat_ori", t."zat_des",
                   t."fexp_vj", h."key_hg" AS "joined_household_key", h."fexp_hg"
            FROM "viajes" AS t
            LEFT JOIN "hogares" AS h ON t."key_hg" = h."key_hg"
            ORDER BY t.rowid
        '''
        records = conn.execute(query).fetchall()
        if len(records) != trip_count:
            raise ODMatrixError("The household join changed the trip row count")

        pair_data: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"sample_trips": 0, "weights": Decimal(0), "weighted_trip_records": 0,
                    "invalid_weight_records": 0, "invalid_household_factors": 0}
        )
        zone_data: dict[str, dict[str, int]] = defaultdict(
            lambda: {"origin_trips": 0, "destination_trips": 0, "intrazonal_trips": 0}
        )
        household_factor_values: dict[str, dict[str, set[Decimal | None]]] = {
            "fexp_hg": defaultdict(set),
            "fexp_vj": defaultdict(set),
        }
        stats: dict[str, dict[str, Any]] = {}
        for field in ("fexp_hg", "fexp_vj"):
            stats[field] = {"nonempty_count": 0, "numeric_count": 0, "missing_count": 0,
                            "non_numeric_count": 0, "zero_count": 0, "negative_count": 0,
                            "valid_sum": Decimal(0), "valid_values": []}

        missing_origin = missing_destination = missing_household_join = 0
        both_zones = intrazonal = factor_mismatch = 0
        for record in records:
            origin = _source_zone(record["zat_ori"])
            destination = _source_zone(record["zat_des"])
            missing_origin += origin is None
            missing_destination += destination is None
            missing_household_join += record["joined_household_key"] is None
            if origin is not None:
                zone_data[origin]["origin_trips"] += 1
            if destination is not None:
                zone_data[destination]["destination_trips"] += 1
            household_key = str(record["key_hg"])
            h_weight = _parse_factor(record["fexp_hg"])
            v_weight = _parse_factor(record["fexp_vj"])
            household_factor_values["fexp_hg"][household_key].add(h_weight)
            household_factor_values["fexp_vj"][household_key].add(v_weight)
            factor_mismatch += h_weight is not None and v_weight is not None and h_weight != v_weight

            for field, raw, parsed in (
                ("fexp_hg", record["fexp_hg"], h_weight),
                ("fexp_vj", record["fexp_vj"], v_weight),
            ):
                current = stats[field]
                is_nonempty = raw is not None and bool(str(raw).strip())
                current["nonempty_count"] += is_nonempty
                if not is_nonempty:
                    current["missing_count"] += 1
                elif parsed is None:
                    current["non_numeric_count"] += 1
                else:
                    current["numeric_count"] += 1
                    current["valid_sum"] += parsed
                    current["valid_values"].append(parsed)
                    current["zero_count"] += parsed == 0
                    current["negative_count"] += parsed < 0

            if origin is None or destination is None:
                continue
            both_zones += 1
            zone_data[origin]["intrazonal_trips"] += int(origin == destination)
            if origin == destination:
                intrazonal += 1
            cell = pair_data[(origin, destination)]
            cell["sample_trips"] += 1
            if h_weight is None or h_weight <= 0:
                cell["invalid_weight_records"] += 1
                cell["invalid_household_factors"] += 1
            else:
                cell["weighted_trip_records"] += 1
                cell["weights"] += h_weight

        if missing_household_join:
            raise ODMatrixError(f"{missing_household_join} trips do not match a household record")

        for field, current in stats.items():
            values = current.pop("valid_values")
            current["min"] = min(values) if values else None
            current["max"] = max(values) if values else None
            current["trip_sum"] = current.pop("valid_sum")
            current["zero_count"] = int(current["zero_count"])
            current["negative_count"] = int(current["negative_count"])
        variable_factor_households = {
            field: sum(len(values) > 1 for values in by_household.values())
            for field, by_household in household_factor_values.items()
        }
        constant_factor_households = {
            field: len(by_household) - variable_factor_households[field]
            for field, by_household in household_factor_values.items()
        }
        invalid_factor_records = sum(cell["invalid_weight_records"] for cell in pair_data.values())
        sample_rows = [
            {"zat_ori": origin, "zat_des": destination, "sample_trips": cell["sample_trips"]}
            for (origin, destination), cell in sorted(pair_data.items())
        ]
        expanded_rows: list[dict[str, Any]] = []
        for (origin, destination), cell in sorted(pair_data.items()):
            complete = cell["invalid_weight_records"] == 0
            expanded_rows.append({
                "zat_ori": origin,
                "zat_des": destination,
                "expanded_trips": cell["weights"] if complete else None,
                "sample_trips": cell["sample_trips"],
                "weighted_trip_records": cell["weighted_trip_records"],
                "invalid_weight_records": cell["invalid_weight_records"],
            })

        expanded_total = sum(
            (row["expanded_trips"] for row in expanded_rows if row["expanded_trips"] is not None),
            Decimal(0),
        )
        benchmark_difference = expanded_total - BENCHMARK if invalid_factor_records == 0 else None
        benchmark_percent = (
            (benchmark_difference / BENCHMARK * Decimal(100)).quantize(Decimal("0.0000001"))
            if benchmark_difference is not None else None
        )
        unique_zones = sorted(zone_data)
        zone_rows = [
            {"zone_code": zone, **zone_data[zone], "geographic_classification": "not_assigned_no_exact_crosswalk"}
            for zone in unique_zones
        ]

        reconciliation = [
            _metric("source_trip_rows", trip_count),
            _metric("unique_trip_keys", distinct_keys),
            _metric("source_household_rows", household_count),
            _metric("trips_missing_origin_code", missing_origin),
            _metric("trips_missing_destination_code", missing_destination),
            _metric("trips_with_both_nonblank_zone_codes", both_zones),
            _metric("sample_matrix_trip_total", sum(row["sample_trips"] for row in sample_rows)),
            _metric("sample_od_pairs", len(sample_rows)),
            _metric("intrazonal_sample_trips", intrazonal),
            _metric("legacy_internal_matrix_trip_count", LEGACY_INTERNAL_TRIP_COUNT, "historical_comparison"),
            _metric("trips_included_beyond_legacy_study_area_scope", both_zones - LEGACY_INTERNAL_TRIP_COUNT, "historical_comparison"),
            _metric("legacy_internal_matrix_intrazonal_trips", LEGACY_INTERNAL_INTRAZONAL_COUNT, "historical_comparison"),
            _metric("intrazonal_trips_added_vs_legacy_scope", intrazonal - LEGACY_INTERNAL_INTRAZONAL_COUNT, "historical_comparison"),
            _metric("distinct_observed_zone_codes", len(unique_zones)),
            _metric("expanded_trip_total", expanded_total if invalid_factor_records == 0 else None,
                    "complete" if invalid_factor_records == 0 else "incomplete_factor_coverage"),
            _metric("trips_with_invalid_household_factor", invalid_factor_records),
            _metric("household_factor_expanded_total_difference_from_benchmark", benchmark_difference,
                    "descriptive_comparison" if benchmark_difference is not None else "not_comparable_partial"),
            _metric("difference_percent_of_benchmark", benchmark_percent,
                    "descriptive_comparison" if benchmark_percent is not None else "not_comparable_partial"),
        ]

        quality_rows = [
            _metric("trip_key_unique_and_nonnull", trip_count, "pass"),
            _metric("household_join_missing_rows", missing_household_join, "pass" if not missing_household_join else "fail"),
            _metric("geographic_crosswalk_applied", "no",
                    "not_used_for_filtering", "Zone identifiers remain source text; no coercion or inferred match is applied."),
            _metric("legacy_study_area_matrix_trip_count", LEGACY_INTERNAL_TRIP_COUNT, "historical_comparison", "Previous release restricted both endpoints to its inferred study-area municipality set."),
            _metric("trips_included_beyond_legacy_study_area_scope", both_zones - LEGACY_INTERNAL_TRIP_COUNT,
                    "historical_comparison", "Included with source zone codes unchanged; not reclassified as external/gateway by this build."),
            _metric("intrazonal_trip_count", intrazonal, "included"),
            _metric("households_with_trips_constant_fexp_hg", constant_factor_households["fexp_hg"]),
            _metric("households_with_trips_variable_fexp_hg", variable_factor_households["fexp_hg"]),
            _metric("households_with_trips_constant_fexp_vj", constant_factor_households["fexp_vj"]),
            _metric("households_with_trips_variable_fexp_vj", variable_factor_households["fexp_vj"]),
            _metric("factor_mismatch_records_fexp_hg_vs_fexp_vj", factor_mismatch,
                    "documented_difference", "Mismatch does not establish which supplied field is erroneous."),
            _metric("published_daily_trip_benchmark", BENCHMARK, "reference_only"),
            _metric("factor_field_fexp_hg_nonempty", stats["fexp_hg"]["nonempty_count"]),
            _metric("factor_field_fexp_hg_numeric", stats["fexp_hg"]["numeric_count"]),
            _metric("factor_field_fexp_hg_non_numeric", stats["fexp_hg"]["non_numeric_count"]),
            _metric("factor_field_fexp_hg_missing", stats["fexp_hg"]["missing_count"]),
            _metric("factor_field_fexp_hg_zero", stats["fexp_hg"]["zero_count"]),
            _metric("factor_field_fexp_hg_negative", stats["fexp_hg"]["negative_count"]),
            _metric("factor_field_fexp_hg_min", stats["fexp_hg"]["min"]),
            _metric("factor_field_fexp_hg_max", stats["fexp_hg"]["max"]),
            _metric("factor_field_fexp_hg_sum_repeated_per_trip", stats["fexp_hg"]["trip_sum"]),
            _metric("factor_field_fexp_vj_nonempty", stats["fexp_vj"]["nonempty_count"]),
            _metric("factor_field_fexp_vj_numeric", stats["fexp_vj"]["numeric_count"]),
            _metric("factor_field_fexp_vj_non_numeric", stats["fexp_vj"]["non_numeric_count"]),
            _metric("factor_field_fexp_vj_missing", stats["fexp_vj"]["missing_count"]),
            _metric("factor_field_fexp_vj_zero", stats["fexp_vj"]["zero_count"]),
            _metric("factor_field_fexp_vj_negative", stats["fexp_vj"]["negative_count"]),
            _metric("factor_field_fexp_vj_min", stats["fexp_vj"]["min"]),
            _metric("factor_field_fexp_vj_max", stats["fexp_vj"]["max"]),
            _metric("factor_field_fexp_vj_sum_diagnostic", stats["fexp_vj"]["trip_sum"]),
        ]

        outputs = {
            SAMPLE_CSV: (sample_rows, ["zat_ori", "zat_des", "sample_trips"], "csv"),
            SAMPLE_PARQUET: (sample_rows, ["zat_ori", "zat_des", "sample_trips"], "parquet"),
            EXPANDED_CSV: (expanded_rows, ["zat_ori", "zat_des", "expanded_trips", "sample_trips", "weighted_trip_records", "invalid_weight_records"], "csv"),
            EXPANDED_PARQUET: (expanded_rows, ["zat_ori", "zat_des", "expanded_trips", "sample_trips", "weighted_trip_records", "invalid_weight_records"], "parquet"),
            RECONCILIATION_CSV: (reconciliation, ["metric", "value", "status", "detail"], "csv"),
            QUALITY_CSV: (quality_rows, ["metric", "value", "status", "detail"], "csv"),
            ZONE_SUMMARY_CSV: (zone_rows, ["zone_code", "origin_trips", "destination_trips", "intrazonal_trips", "geographic_classification"], "csv"),
        }
        staged: dict[Path, Path] = {}
        try:
            for relative, (rows, fields, output_format) in outputs.items():
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                handle = tempfile.NamedTemporaryFile(
                    mode="wb" if output_format == "parquet" else "w",
                    encoding=None if output_format == "parquet" else "utf-8-sig",
                    newline=None if output_format == "parquet" else "",
                    dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False,
                )
                temp_path = Path(handle.name)
                handle.close()
                staged[relative] = temp_path
                if output_format == "csv":
                    _write_csv(temp_path, fields, rows)
                elif relative == SAMPLE_PARQUET:
                    schema = pa.schema([pa.field("zat_ori", pa.string(), nullable=False), pa.field("zat_des", pa.string(), nullable=False), pa.field("sample_trips", pa.int64(), nullable=False)])
                    pq.write_table(pa.Table.from_pylist(rows, schema=schema), temp_path, compression="zstd")
                else:
                    _write_parquet(temp_path, rows, fields)

            # Read staged matrix artifacts back and validate row counts, columns, and pair keys.
            staged_sample = staged[SAMPLE_PARQUET]
            staged_expanded = staged[EXPANDED_PARQUET]
            sample_check = pq.read_table(staged_sample)
            expanded_check = pq.read_table(staged_expanded)
            if sample_check.num_rows != len(sample_rows) or expanded_check.num_rows != len(expanded_rows):
                raise ODMatrixError("Staged Parquet matrix row counts failed validation")
            sample_pairs = list(zip(sample_check.column("zat_ori").to_pylist(), sample_check.column("zat_des").to_pylist(), strict=True))
            expanded_pairs = list(zip(expanded_check.column("zat_ori").to_pylist(), expanded_check.column("zat_des").to_pylist(), strict=True))
            if sample_pairs != expanded_pairs:
                raise ODMatrixError("Sample and expanded matrices do not have the same OD pair rows")
            if sum(sample_check.column("sample_trips").to_pylist()) != both_zones:
                raise ODMatrixError("Staged sample matrix does not reconcile to trips with two usable zones")
            if sum(row["sample_trips"] for row in expanded_rows) != both_zones:
                raise ODMatrixError("Expanded matrix sample trip counts do not reconcile")
            expanded_numbers = expanded_check.column("expanded_trips").to_pylist()
            if invalid_factor_records == 0 and sum(expanded_numbers, Decimal(0)) != expanded_total:
                raise ODMatrixError("Staged expanded values do not reconcile to the household-factor sum")

            for relative, (expected_rows, expected_fields, output_format) in outputs.items():
                if relative not in (SAMPLE_CSV, EXPANDED_CSV):
                    continue
                with staged[relative].open("r", encoding="utf-8-sig", newline="") as stream:
                    reader = csv.DictReader(stream, strict=True)
                    if reader.fieldnames != expected_fields:
                        raise ODMatrixError(f"Staged CSV header failed validation: {relative.as_posix()}")
                    read_rows = list(reader)
                if len(read_rows) != len(expected_rows):
                    raise ODMatrixError(f"Staged CSV row count failed validation: {relative.as_posix()}")
                for csv_row, expected_row in zip(read_rows, expected_rows, strict=True):
                    if csv_row["zat_ori"] != expected_row["zat_ori"] or csv_row["zat_des"] != expected_row["zat_des"]:
                        raise ODMatrixError(f"Staged CSV zone identifiers changed: {relative.as_posix()}")
                    value_field = "sample_trips" if relative == SAMPLE_CSV else "expanded_trips"
                    expected_value = expected_row[value_field]
                    if expected_value is None:
                        if csv_row[value_field] != "":
                            raise ODMatrixError(f"Staged CSV missing value changed: {relative.as_posix()}")
                    elif Decimal(csv_row[value_field]) != Decimal(str(expected_value)):
                        raise ODMatrixError(f"Staged CSV matrix values changed: {relative.as_posix()}")

            output_dir = root / METHODOLOGY_MD
            output_dir.parent.mkdir(parents=True, exist_ok=True)
            method_temp = tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=output_dir.parent,
                prefix=f".{output_dir.name}.", suffix=".tmp", delete=False,
            )
            method_temp.close()
            method_path = Path(method_temp.name)
            staged[METHODOLOGY_MD] = method_path
            summary = {
                "source_trip_rows": trip_count,
                "sample_trips": both_zones,
                "sample_od_pairs": len(sample_rows),
                "intrazonal_trips": intrazonal,
                "invalid_weight_records": invalid_factor_records,
                "expanded_total": expanded_total,
                "benchmark_difference": benchmark_difference,
                "benchmark_difference_percent": benchmark_percent,
                "factor_mismatch_records": factor_mismatch,
                "variable_fexp_hg_households": variable_factor_households["fexp_hg"],
                "variable_fexp_vj_households": variable_factor_households["fexp_vj"],
            }
            _write_methodology(method_path, summary, stats)
            for relative, temp_path in staged.items():
                os.replace(temp_path, root / relative)
        finally:
            for temp_path in staged.values():
                temp_path.unlink(missing_ok=True)

        return {"outputs": [relative.as_posix() for relative in outputs], "summary": summary,
                "factor_diagnostics": stats}
    except ODMatrixError:
        raise
    except Exception as exc:
        raise ODMatrixError(f"OD construction failed ({type(exc).__name__})") from exc
    finally:
        if conn is not None:
            conn.close()
