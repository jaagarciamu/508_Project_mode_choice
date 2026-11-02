"""Read-only inventory helpers for the local EM2023 source tree."""

from __future__ import annotations

import csv
import codecs
import json
from collections import Counter
from pathlib import Path
from typing import Any


RAW_RELATIVE_PATH = Path("data/sources/raw")
CATALOG_RELATIVE_PATH = Path("docs/data_dictionary")


def _category(relative_path: Path) -> str:
    parts = [part.casefold() for part in relative_path.parts]
    if not parts:
        return "supporting_material"
    if parts[0] == "eodi":
        if len(parts) > 1 and parts[1].startswith("01_"):
            return "eodi_technical_documentation"
        if len(parts) > 1 and parts[1].startswith("02_"):
            return "eodi_survey_instruments"
        if len(parts) > 1 and parts[1].startswith("03_"):
            return "eodi_counts_and_geospatial_references"
        if len(parts) > 1 and parts[1].startswith("04_"):
            return "eodi_intercept_survey_data"
        return "eodi_supporting_material"
    if parts[0] == "database":
        return "em2023_microdata"
    if parts[0] == "documentation":
        return "em2023_documentation"
    if parts[0] == "contrato 2022-1972":
        return "contract_context"
    if parts[0] == "formularios":
        return "survey_instruments"
    if parts[0] == "datos tecnicos de la encuesta":
        return "survey_technical_documentation"
    if parts[0] == "zonification":
        return "geographic_reference"
    return "supporting_material"


def _read_csv_header(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    encoding = ""
    with path.open("rb") as stream:
        header_bytes = stream.readline()
    if not header_bytes:
        return {
            "csv_encoding": None,
            "csv_delimiter": None,
            "headers": [],
            "column_count": 0,
            "empty_header_positions": [],
            "whitespace_header_names": [],
            "duplicate_headers": [],
            "metadata_status": "empty_file",
        }

    header_line = ""
    for candidate in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            decoder = codecs.getincrementaldecoder(candidate)(errors="strict")
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    decoder.decode(chunk, final=False)
                decoder.decode(b"", final=True)
            header_line = header_bytes.decode(candidate).rstrip("\r\n")
            encoding = candidate
            break
        except UnicodeDecodeError as exc:
            errors.append(f"{candidate}: {exc}")
    if not encoding:
        return {"metadata_status": f"encoding_error: {'; '.join(errors)}"}

    try:
        dialect = csv.Sniffer().sniff(header_line, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    headers = next(csv.reader([header_line], dialect))

    counts = Counter(headers)
    return {
        "csv_encoding": encoding,
        "csv_delimiter": dialect.delimiter,
        "headers": headers,
        "column_count": len(headers),
        "empty_header_positions": [index + 1 for index, name in enumerate(headers) if not name],
        "whitespace_header_names": [name for name in headers if name != name.strip()],
        "duplicate_headers": sorted(name for name, count in counts.items() if count > 1),
        "metadata_status": "ok",
    }


def _read_xlsx_metadata(path: Path) -> dict[str, Any]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return {"metadata_status": "openpyxl_missing; install the source-docs extra"}

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheets = [
            {
                "name": sheet.title,
                "max_row": sheet.max_row,
                "max_column": sheet.max_column,
            }
            for sheet in workbook.worksheets
        ]
    finally:
        workbook.close()
    return {"xlsx_sheets": sheets, "metadata_status": "ok"}


def _read_pdf_metadata(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"metadata_status": "pypdf_missing; install the source-docs extra"}

    reader = PdfReader(path, strict=False)
    metadata = reader.metadata
    title = metadata.title if metadata else None
    return {
        "pdf_title": title,
        "pdf_page_count": len(reader.pages),
        "metadata_status": "ok",
    }


def build_inventory(project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inventory files and CSV column names without reading data rows."""
    raw_root = project_root / RAW_RELATIVE_PATH
    if not raw_root.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {raw_root}")

    inventory: list[dict[str, Any]] = []
    schemas: list[dict[str, Any]] = []
    for path in sorted((item for item in raw_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold()):
        relative_path = path.relative_to(project_root).as_posix()
        relative_to_raw = path.relative_to(raw_root)
        suffix = path.suffix.casefold()
        row: dict[str, Any] = {
            "source_path": relative_path,
            "category": _category(relative_to_raw),
            "format": suffix.lstrip(".") or "no_extension",
            "size_bytes": path.stat().st_size,
            "csv_encoding": None,
            "csv_delimiter": None,
            "column_count": None,
            "headers_json": None,
            "empty_header_positions_json": None,
            "whitespace_header_names_json": None,
            "duplicate_headers_json": None,
            "xlsx_sheets_json": None,
            "pdf_title": None,
            "pdf_page_count": None,
            "metadata_status": "file_metadata_only",
        }

        if suffix == ".csv":
            metadata = _read_csv_header(path)
            for key in ("csv_encoding", "csv_delimiter", "column_count", "metadata_status"):
                row[key] = metadata.get(key)
            row["headers_json"] = json.dumps(metadata.get("headers", []), ensure_ascii=False)
            row["empty_header_positions_json"] = json.dumps(metadata.get("empty_header_positions", []), ensure_ascii=False)
            row["whitespace_header_names_json"] = json.dumps(metadata.get("whitespace_header_names", []), ensure_ascii=False)
            row["duplicate_headers_json"] = json.dumps(metadata.get("duplicate_headers", []), ensure_ascii=False)
            candidate_identifiers = [
                name
                for name in metadata.get("headers", [])
                if name.casefold().startswith("key_")
                or name.casefold() in {"cod_viv", "cod_hog", "cod_vh", "cod_per", "cod_pers", "cod_vj", "cod_eta"}
            ]
            schemas.append(
                {
                    "source_path": relative_path,
                    "encoding": metadata.get("csv_encoding"),
                    "delimiter": metadata.get("csv_delimiter"),
                    "candidate_identifiers_unverified": candidate_identifiers,
                    "candidate_status": "name_based_candidates_only; uniqueness_and_scope_not_tested",
                    "columns": [
                        {
                            "source_name": name,
                            "documented_definition": None,
                            "definition_status": "pending_document_review",
                        }
                        for name in metadata.get("headers", [])
                    ],
                    "structural_anomalies": {
                        "empty_header_positions": metadata.get("empty_header_positions", []),
                        "whitespace_header_names": metadata.get("whitespace_header_names", []),
                        "duplicate_headers": metadata.get("duplicate_headers", []),
                    },
                }
            )
        elif suffix == ".xlsx":
            metadata = _read_xlsx_metadata(path)
            if "xlsx_sheets" in metadata:
                row["xlsx_sheets_json"] = json.dumps(metadata["xlsx_sheets"], ensure_ascii=False)
            row["metadata_status"] = metadata["metadata_status"]
        elif suffix == ".pdf":
            try:
                metadata = _read_pdf_metadata(path)
                row.update({key: value for key, value in metadata.items() if key in {"pdf_title", "pdf_page_count"}})
                row["metadata_status"] = metadata["metadata_status"]
            except Exception as exc:  # report a safe parse status, not document contents
                row["metadata_status"] = f"pdf_metadata_error: {type(exc).__name__}"

        inventory.append(row)
    return inventory, schemas


def write_catalogs(project_root: Path) -> tuple[Path, Path]:
    """Write a file catalog and preliminary header dictionary under docs/."""
    inventory, schemas = build_inventory(project_root)
    output_dir = project_root / CATALOG_RELATIVE_PATH
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = output_dir / "source_inventory.csv"
    fieldnames = list(inventory[0]) if inventory else []
    with catalog_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory)

    schema_path = output_dir / "source_schema.json"
    schema_path.write_text(
        json.dumps(schemas, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return catalog_path, schema_path
