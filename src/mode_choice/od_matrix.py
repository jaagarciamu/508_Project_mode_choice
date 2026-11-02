"""Build auditable, sample-count EODH origin-destination products."""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import tempfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
import shapefile

DATABASE = Path("data/relational/em2023_relational.sqlite")
ZONING_DBF = Path("data/sources/raw/zonification/ZAT2023.dbf")
OUTPUT = Path("data/analytical/od_matrices")
STUDY_MUNICIPALITY_CODES = {11001, 25099, 25126, 25175, 25181, 25214, 25260, 25269, 25286, 25295, 25377, 25430, 25473, 25740, 25754, 25758, 25769, 25785, 25799, 25817, 25899}
EXPANSION_DOCUMENTATION_VALIDATED = False


class ODMatrixError(RuntimeError):
    """Raised when a safe OD product cannot be built."""


def _zone_key(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return f"invalid:{raw}"
    if not number.is_finite() or number != number.to_integral_value():
        return f"invalid:{raw}"
    return str(int(number))


def _load_zones(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    reader = shapefile.Reader(dbf=str(path), encoding="utf-8")
    names = [field[0] for field in reader.fields[1:]]
    required = {"ZAT", "MUNCod", "NOMMun"}
    if not required.issubset(names):
        raise ODMatrixError("The ZAT attribute table is missing required fields")
    zones: dict[str, dict[str, Any]] = {}
    for record in reader.records():
        row = dict(zip(names, record))
        key = _zone_key(row["ZAT"])
        if key is None or key.startswith("invalid:") or key in zones:
            raise ODMatrixError("The ZAT geography contains a missing, invalid, or duplicated ZAT code")
        mun_key = _zone_key(row["MUNCod"])
        try:
            municipality_code = int(mun_key) if mun_key is not None else None
        except ValueError:
            municipality_code = None
        zones[key] = {"municipality_code": municipality_code, "municipality_name": str(row["NOMMun"]).strip()}
    return zones, {"zone_count": len(zones), "study_area_zone_count": sum(z["municipality_code"] in STUDY_MUNICIPALITY_CODES for z in zones.values()), "external_or_gateway_zone_count": sum(z["municipality_code"] not in STUDY_MUNICIPALITY_CODES for z in zones.values())}


def _classify_zone(value: Any, zones: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    key = _zone_key(value)
    if key is None:
        return "missing_zone", None
    if key.startswith("invalid:"):
        return "invalid_zone_code", None
    zone = zones.get(key)
    if zone is None:
        return "unmatched_zone", key
    if zone["municipality_code"] in STUDY_MUNICIPALITY_CODES:
        return "study_area_zone", key
    return "external_or_gateway_zone", key


def _safe_label(value: Any) -> str:
    """Normalize only empty mode values into an explicit reporting bucket."""
    if value is None or not str(value).strip():
        return "[unclassified]"
    return str(value)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def _publish(staged: Path, output: Path) -> None:
    backup = output.with_name(f".{output.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    had_output = output.exists()
    try:
        if had_output:
            os.replace(output, backup)
        os.replace(staged, output)
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        if had_output and backup.exists():
            os.replace(backup, output)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def build_od_products(project_root: Path) -> dict[str, Any]:
    """Build sample OD matrices and aggregate reconciliation reports atomically."""
    root = Path(project_root).resolve()
    db_path, dbf_path = root / DATABASE, root / ZONING_DBF
    output = root / OUTPUT
    for required_path in (db_path, dbf_path):
        if not required_path.is_file():
            raise ODMatrixError(f"Required input not found: {required_path.relative_to(root).as_posix()}")
    try:
        zones, zone_summary = _load_zones(dbf_path)
        connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            columns = {row[1] for row in connection.execute('PRAGMA table_info("viajes")')}
            required = {"key_viaje", "zat_ori", "zat_des", "modo_principal_agrupado", "fexp_vj"}
            if not required.issubset(columns):
                raise ODMatrixError("The viajes table is missing required source fields")
            count, distinct, null = connection.execute('SELECT COUNT(*), COUNT(DISTINCT "key_viaje"), SUM("key_viaje" IS NULL) FROM "viajes"').fetchone()
            if count != distinct or null:
                raise ODMatrixError("The source trip key is not unique and non-null")
            rows = pd.read_sql_query('SELECT "key_viaje", "zat_ori", "zat_des", "modo_principal_agrupado", "fexp_vj" FROM "viajes"', connection)
        finally:
            connection.close()
        origin = [_classify_zone(v, zones) for v in rows["zat_ori"]]
        destination = [_classify_zone(v, zones) for v in rows["zat_des"]]
        rows["origin_status"] = [s for s, _ in origin]
        rows["destination_status"] = [s for s, _ in destination]
        rows["origin_zone"] = [z for _, z in origin]
        rows["destination_zone"] = [z for _, z in destination]
        rows["mode_category"] = rows["modo_principal_agrupado"].map(_safe_label)
        rows["eligible_od"] = (rows.origin_status == "study_area_zone") & (rows.destination_status == "study_area_zone")
        od = rows.loc[rows.eligible_od]
        if od[["origin_zone", "destination_zone"]].isna().any().any():
            raise ODMatrixError("Eligible OD records contain unresolved zone codes")
        total = od.groupby(["origin_zone", "destination_zone"], as_index=False, sort=True).size().rename(columns={"origin_zone":"zat_ori", "destination_zone":"zat_des", "size":"sample_trips"})
        by_mode = od.groupby(["origin_zone", "destination_zone", "mode_category"], as_index=False, sort=True).size().rename(columns={"origin_zone":"zat_ori", "destination_zone":"zat_des", "mode_category":"modo_principal_agrupado", "size":"sample_trips"})
        classified = od.loc[od.mode_category != "[unclassified]"]
        unclassified_n = int((od.mode_category == "[unclassified]").sum())
        mode_by_od = by_mode.groupby(["zat_ori", "zat_des"], as_index=False)["sample_trips"].sum()
        compare = total.merge(mode_by_od, on=["zat_ori", "zat_des"], how="outer", suffixes=("_total", "_by_mode"), indicator=True)
        if (compare["_merge"] != "both").any() or (compare["sample_trips_total"] != compare["sample_trips_by_mode"]).any():
            raise ODMatrixError("The complete OD matrix does not equal the sum of source-mode matrices by OD pair")
        if int(by_mode.sample_trips.sum()) != len(od) or int(classified.shape[0]) + unclassified_n != len(od):
            raise ODMatrixError("Mode totals do not reconcile to the complete sample OD universe")
        # The factor remains an unapplied source field until its field-level definition and operational universe are documented.
        factor = rows["fexp_vj"].astype("string")
        def parse_factor(value: Any) -> float | None:
            if value is None or pd.isna(value) or not str(value).strip():
                return None
            text = str(value).strip()
            # Source storage uses a decimal comma and, for some values, a dot thousands separator.
            if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+),\d+", text):
                return None
            try:
                return float(Decimal(text.replace(".", "").replace(",", ".")))
            except InvalidOperation:
                return None
        numeric = pd.Series([parse_factor(value) for value in factor], dtype="Float64")
        factor_report = pd.DataFrame([{
            "source_trip_rows": len(rows), "factor_nonempty_rows": int(factor.fillna("").str.strip().ne("").sum()),
            "factor_numeric_rows": int(numeric.notna().sum()), "factor_non_numeric_rows": int((factor.fillna("").str.strip().ne("") & numeric.isna()).sum()),
            "factor_missing_or_blank_rows": int((factor.isna() | factor.fillna("").str.strip().eq("")).sum()),
            "factor_negative_rows": int((numeric < 0).sum()), "factor_zero_rows": int((numeric == 0).sum()),
            "factor_sum_diagnostic_not_applied": float(numeric.sum()) if numeric.notna().any() else None,
            "expansion_release_status": "not_published_documentary_validation_pending",
            "expansion_documentation_validated": EXPANSION_DOCUMENTATION_VALIDATED,
        }])
        endpoint_counts = Counter()
        for status in rows.origin_status:
            endpoint_counts[f"origin_{status}"] += 1
        for status in rows.destination_status:
            endpoint_counts[f"destination_{status}"] += 1
        pair_status = rows.assign(pair_status=rows.origin_status + "__to__" + rows.destination_status).groupby("pair_status", as_index=False).size().rename(columns={"size":"trip_rows"})
        reconciliation = pd.DataFrame([
            {"metric":"source_trip_rows", "count":len(rows)},
            {"metric":"unique_trip_keys", "count":int(distinct)},
            {"metric":"sample_matrix_in_scope_trips", "count":len(od)},
            {"metric":"sample_trips_with_classified_source_mode", "count":len(classified)},
            {"metric":"sample_trips_with_unclassified_mode", "count":unclassified_n},
            {"metric":"intrazonal_sample_trips", "count":int((od.origin_zone == od.destination_zone).sum())},
            {"metric":"sample_od_pairs", "count":len(total)},
            {"metric":"sample_od_mode_pairs", "count":len(by_mode)},
        ] + [{"metric":key,"count":value} for key,value in sorted(endpoint_counts.items())])
        manifest = {
            "product": "EM2023 EODH sample daily OD matrices", "status": "sample_products_published_expansion_pending_documentary_validation",
            "source_database": DATABASE.as_posix(), "source_table": "viajes", "source_row_count": len(rows), "trip_key_unique": True,
            "zone_source": ZONING_DBF.as_posix(), "zone_count": zone_summary["zone_count"],
            "official_release_page": "https://observatorio.movilidadbogota.gov.co/publicaciones/resultados/encuesta-de-movilidad-2023", "official_release_review_date": "2026-11-02",
            "study_area_municipality_codes": sorted(STUDY_MUNICIPALITY_CODES), "study_area_zone_count": zone_summary["study_area_zone_count"],
            "external_or_gateway_zone_count": zone_summary["external_or_gateway_zone_count"],
            "matrix_universe": "all source viajes records with both endpoints assigned to ZAT2023 features in Bogota or the 20 study municipalities; no additional record-level eligibility filter applied; intrazonal trips retained",
            "sample_complete_matrix": "eodh_sample_od_total.csv", "sample_by_mode_matrix": "eodh_sample_od_by_mode.csv",
            "weighted_matrices_published": False, "weight_field": "fexp_vj", "weighting_status": "retained as source text; not applied",
            "weighting_reason": "official material documents a model-based doubly robust estimator but does not establish the field-level derivation, valid trip universe, or operational use of fexp_vj",
            "uncertainty": "not estimated; no reproducible model-based variance procedure located for OD-by-mode cells",
            "outputs_contain_trip_identifiers": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".od_matrices.", dir=output.parent) as tmp:
            staged = Path(tmp) / OUTPUT.name
            staged.mkdir()
            _write_csv(staged / "eodh_sample_od_total.csv", total)
            _write_csv(staged / "eodh_sample_od_by_mode.csv", by_mode)
            _write_csv(staged / "eodh_sample_reconciliation.csv", reconciliation)
            _write_csv(staged / "eodh_sample_geography_pair_status.csv", pair_status)
            _write_csv(staged / "eodh_factor_diagnostic.csv", factor_report)
            (staged / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            # Validate staged artifacts before swapping the product directory.
            total_check = pd.read_csv(staged / "eodh_sample_od_total.csv")
            mode_check = pd.read_csv(staged / "eodh_sample_od_by_mode.csv")
            if int(total_check.sample_trips.sum()) != len(od) or int(mode_check.sample_trips.sum()) != len(od):
                raise ODMatrixError("Staged matrices failed trip-count reconciliation")
            _publish(staged, output)
        return {"output_directory": output, "summary": reconciliation, "geography": zone_summary, "factor": factor_report, "weighted_products_published": False}
    except ODMatrixError:
        raise
    except Exception as exc:
        raise ODMatrixError(f"OD construction failed ({type(exc).__name__})") from exc
