from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_COLUMNS = [
    "person_id",
    "full_name",
    "current_role",
    "home_location",
    "timezone",
    "internal_external",
    "practice",
    "source_type",
    "source_system",
    "source_record_id",
]


BOOLEAN_COLUMNS = {
    "interviewer_suitable",
    "willing_to_interview",
    "willing_to_support_pocs",
}

INTEGER_COLUMNS = {
    "prior_interview_count",
    "poc_participation_count",
    "presales_participation_count",
}

FLOAT_COLUMNS = {
    "profile_confidence",
}

LIST_COLUMNS = {
    "top_clients",
    "top_domains",
}


class CsvImportError(ValueError):
    """Raised when the pilot CSV cannot be converted into canonical JSON records."""


def _parse_boolean(value: str, column_name: str, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    raise CsvImportError(
        f"Row {row_number}: column '{column_name}' must be true/false (or yes/no), got '{value}'."
    )


def _parse_integer(value: str, column_name: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CsvImportError(f"Row {row_number}: column '{column_name}' must be an integer, got '{value}'.") from exc


def _parse_float(value: str, column_name: str, row_number: int) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise CsvImportError(f"Row {row_number}: column '{column_name}' must be numeric, got '{value}'.") from exc


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


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
            f"{readable}. Check README for the pilot intake template column list."
        )


def _validate_required_values(row: dict[str, str], row_number: int) -> None:
    missing_values = [column for column in REQUIRED_COLUMNS if not row.get(column, "").strip()]
    if missing_values:
        readable = ", ".join(missing_values)
        raise CsvImportError(
            f"Row {row_number}: missing required value(s): {readable}. "
            "Please fill the core fields before importing."
        )


def _row_to_person_record(row: dict[str, str], row_number: int) -> dict:
    _validate_required_values(row=row, row_number=row_number)

    record: dict[str, object] = {
        "person_id": row["person_id"].strip(),
        "full_name": row["full_name"].strip(),
        "current_role": row["current_role"].strip(),
        "home_location": row["home_location"].strip(),
        "timezone": row["timezone"].strip(),
        "summary": row.get("summary", "").strip(),
        "internal_external": row["internal_external"].strip().lower(),
        "practice": row["practice"].strip(),
        "source_provenance": {
            "source_type": row["source_type"].strip(),
            "source_system": row["source_system"].strip(),
            "source_record_id": row["source_record_id"].strip(),
        },
    }

    for column_name in BOOLEAN_COLUMNS:
        value = row.get(column_name, "").strip()
        if value:
            record[column_name] = _parse_boolean(value=value, column_name=column_name, row_number=row_number)

    for column_name in INTEGER_COLUMNS:
        value = row.get(column_name, "").strip()
        if value:
            record[column_name] = _parse_integer(value=value, column_name=column_name, row_number=row_number)

    for column_name in FLOAT_COLUMNS:
        value = row.get(column_name, "").strip()
        if value:
            record[column_name] = _parse_float(value=value, column_name=column_name, row_number=row_number)

    for column_name in LIST_COLUMNS:
        value = row.get(column_name, "").strip()
        if value:
            record[column_name] = _parse_list(value)

    for date_key in ["profile_last_updated_at", "last_verified_at"]:
        value = _clean_optional(row=row, key=date_key)
        if value is not None:
            record[date_key] = value

    for text_key in ["client_facing_comfort"]:
        value = _clean_optional(row=row, key=text_key)
        if value is not None:
            record[text_key] = value.lower()

    return record


def import_pilot_people_csv(input_path: Path, output_path: Path) -> tuple[int, Path]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_required_columns(reader.fieldnames)

        records: list[dict] = []
        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(_row_to_person_record(row=row, row_number=index))

    if not records:
        raise CsvImportError("No importable data rows found. Add at least one populated row below the header.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=2)
        json_file.write("\n")

    return len(records), output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import pilot people CSV into DynPro canonical person JSON format.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to pilot CSV file.",
    )
    parser.add_argument(
        "--output",
        default=Path("data/sample_json/person.imported.json"),
        type=Path,
        help="Path to output JSON file (default: data/sample_json/person.imported.json).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        count, output_path = import_pilot_people_csv(input_path=args.input, output_path=args.output)
    except CsvImportError as error:
        print(f"Pilot CSV import failed: {error}")
        return 1
    except FileNotFoundError:
        print(f"Pilot CSV import failed: file not found: {args.input}")
        return 1

    print(f"Imported {count} people row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
