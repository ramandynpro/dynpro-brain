from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_COLUMNS = [
    "edge_id",
    "from_person_id",
    "to_person_id",
    "relationship_type",
]

FLOAT_COLUMNS = {
    "strength",
    "confidence",
}


class CsvImportError(ValueError):
    """Raised when pilot relationship-edge CSV cannot be mapped to canonical JSON."""


def _parse_float(value: str, column_name: str, row_number: int) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise CsvImportError(
            f"Row {row_number}: column '{column_name}' must be numeric, got '{value}'."
        ) from exc


def _clean_optional(row: dict[str, str], key: str) -> str | None:
    value = row.get(key, "").strip()
    return value or None


def _validate_required_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise CsvImportError("CSV appears empty. Please include a header row and at least one data row.")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        readable = ", ".join(missing_columns)
        raise CsvImportError(
            "CSV is missing required column(s): "
            f"{readable}. Check README for the relationship-edge intake template column list."
        )


def _validate_required_values(row: dict[str, str], row_number: int) -> None:
    missing_values = [column for column in REQUIRED_COLUMNS if not row.get(column, "").strip()]
    if missing_values:
        readable = ", ".join(missing_values)
        raise CsvImportError(
            f"Row {row_number}: missing required value(s): {readable}. "
            "Please fill edge_id, from_person_id, to_person_id, and relationship_type before importing."
        )


def _row_to_relationship_record(row: dict[str, str], row_number: int) -> dict:
    _validate_required_values(row=row, row_number=row_number)

    edge_id = row["edge_id"].strip()
    record: dict[str, object] = {
        "edge_id": edge_id,
        "from_person_id": row["from_person_id"].strip(),
        "to_person_id": row["to_person_id"].strip(),
        "relationship_type": row["relationship_type"].strip(),
    }

    for key in ["context", "last_verified_at"]:
        value = _clean_optional(row=row, key=key)
        if value is not None:
            record[key] = value

    for column_name in FLOAT_COLUMNS:
        value = row.get(column_name, "").strip()
        if value:
            record[column_name] = _parse_float(value=value, column_name=column_name, row_number=row_number)

    source_provenance: dict[str, str] = {}
    for key in ["source_type", "source_system", "source_record_id"]:
        value = _clean_optional(row=row, key=key)
        if value is not None:
            source_provenance[key] = value
    if source_provenance:
        record["source_provenance"] = source_provenance

    return record


def import_pilot_relationship_csv(input_path: Path, output_path: Path) -> tuple[int, Path]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_required_columns(reader.fieldnames)

        records: list[dict] = []
        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(_row_to_relationship_record(row=row, row_number=index))

    if not records:
        raise CsvImportError("No importable data rows found. Add at least one populated row below the header.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=2)
        json_file.write("\n")

    return len(records), output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import pilot relationship-edge CSV into DynPro canonical relationship-edge JSON format.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to pilot relationship-edge CSV file.")
    parser.add_argument(
        "--output",
        default=Path("data/sample_json/relationship_edge.imported.json"),
        type=Path,
        help="Path to output JSON file (default: data/sample_json/relationship_edge.imported.json).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        count, output_path = import_pilot_relationship_csv(input_path=args.input, output_path=args.output)
    except CsvImportError as error:
        print(f"Pilot relationship-edge CSV import failed: {error}")
        return 1
    except FileNotFoundError:
        print(f"Pilot relationship-edge CSV import failed: file not found: {args.input}")
        return 1

    print(f"Imported {count} relationship-edge row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
