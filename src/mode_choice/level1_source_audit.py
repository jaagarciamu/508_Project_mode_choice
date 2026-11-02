"""Read structural EODI workbook metadata without exposing observation rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


EODI_WORKBOOKS = {
    "intercept_survey": Path(
        "data/sources/raw/EODI/04_Base datos/"
        "a. Base de datos con factores de ponderacion y sin dobles conteos.xlsx"
    ),
    "traffic_counts": Path(
        "data/sources/raw/EODI/03_Aforos/"
        "a. Base de datos aforos hora de maxima demanda.xlsx"
    ),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def build_eodi_workbook_catalog(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return workbook/sheet metadata and documented fields, never BD rows."""
    workbooks: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    for role, relative_path in EODI_WORKBOOKS.items():
        path = project_root / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Required EODI source is missing: {relative_path.as_posix()}")
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in workbook.worksheets:
                workbooks.append(
                    {
                        "source_role": role,
                        "source_path": relative_path.as_posix(),
                        "sheet_name": sheet.title,
                        "max_row_including_header": sheet.max_row,
                        "max_column": sheet.max_column,
                        "observation_rows_if_header_row": max(sheet.max_row - 1, 0),
                    }
                )
                if sheet.title.casefold() == "bd":
                    # Only read row 1: source field names, not observation values.
                    headers = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
                    for position, header in enumerate(headers, start=1):
                        fields.append(
                            {
                                "source_role": role,
                                "source_path": relative_path.as_posix(),
                                "sheet_name": sheet.title,
                                "source_position_1based": position,
                                "source_field_name": _text(header),
                                "header_status": "blank_source_header" if header is None or header == "" else "source_header",
                                "documented_definition": "",
                                "documented_values_or_range": "",
                                "definition_status": "pending_dictionary_match",
                            }
                        )
                if sheet.title.casefold() == "dicc":
                    # DICC is source documentation, not survey observations.
                    rows = sheet.iter_rows(values_only=True)
                    next(rows, None)
                    for row in rows:
                        if not row or row[0] is None or not _text(row[0]).strip():
                            continue
                        fields.append(
                            {
                                "source_role": role,
                                "source_path": relative_path.as_posix(),
                                "sheet_name": sheet.title,
                                "source_position_1based": "",
                                "source_field_name": _text(row[0]),
                                "header_status": "dictionary_entry",
                                "documented_definition": _text(row[1]) if len(row) > 1 else "",
                                "documented_values_or_range": _text(row[2]) if len(row) > 2 else "",
                                "definition_status": "source_dictionary_text; field_match_pending",
                            }
                        )
        finally:
            workbook.close()
    return workbooks, fields


def write_eodi_workbook_catalogs(project_root: Path) -> tuple[Path, Path]:
    """Write structural catalogs only after all required workbooks are readable."""
    workbooks, fields = build_eodi_workbook_catalog(project_root)
    output_dir = project_root / "docs/data_dictionary"
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / "eodi_workbook_catalog.csv", output_dir / "eodi_field_dictionary.csv"]
    for path, rows in zip(outputs, (workbooks, fields), strict=True):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
    return outputs[0], outputs[1]
