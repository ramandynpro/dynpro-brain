from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_BASE_COLUMNS = [
    "commercial_id",
    "person_id",
    "engagement_model",
    "currency",
]

RATE_GROUPS = [
    ("cost_rate", "cost_rate_band"),
    ("bill_rate", "target_bill_rate"),
]

OPTIONAL_FLOAT_COLUMNS = {
    "cost_rate",
    "bill_rate",
    "target_bill_rate",
    "confidence",
}

OPTIONAL_INT_COLUMNS = {
    "availability_percent",
}


class CsvImportError(ValueError):
    """Raised when pilot commercial CSV cannot be mapped to canonical JSON."""


def _parse_float(value: str, column_name: str, row_number: int) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise CsvImportError(
            f"Row {row_number}: column '{column_name}' must be numeric, got '{value}'."
        ) from exc


def _parse_int(value: str, column_name: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CsvImportError(
            f"Row {row_number}: column '{column_name}' must be a whole number, got '{value}'."
        ) from exc


def _clean_optional(row: dict[str, str], key: str) -> str | None:
    value = row.get(key, "").strip()
    return value or None


def _validate_required_columns(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise CsvImportError("CSV appears empty. Please include a header row and at least one data row.")

    missing_base = [column for column in REQUIRED_BASE_COLUMNS if column not in fieldnames]
    if missing_base:
        readable = ", ".join(missing_base)
        raise CsvImportError(
            "CSV is missing required column(s): "
            f"{readable}. Check README for the commercial-profile intake template column list."
        )

    for left, right in RATE_GROUPS:
        if left not in fieldnames and right not in fieldnames:
            raise CsvImportError(
                f"CSV must include at least one of '{left}' or '{right}' columns in the header."
            )


def _validate_required_values(row: dict[str, str], row_number: int) -> None:
    missing_values = [column for column in REQUIRED_BASE_COLUMNS if not row.get(column, "").strip()]

    if not (row.get("cost_rate", "").strip() or row.get("cost_rate_band", "").strip()):
        missing_values.append("cost_rate or cost_rate_band")

    if not (row.get("bill_rate", "").strip() or row.get("target_bill_rate", "").strip()):
        missing_values.append("bill_rate or target_bill_rate")

    if missing_values:
        readable = ", ".join(missing_values)
        raise CsvImportError(
            f"Row {row_number}: missing required value(s): {readable}. "
            "Please complete required commercial profile fields before importing."
        )


def _row_to_commercial_record(row: dict[str, str], row_number: int) -> dict:
    _validate_required_values(row=row, row_number=row_number)

    commercial_id = row["commercial_id"].strip()
    record: dict[str, object] = {
        "commercial_profile_id": commercial_id,
        "person_id": row["person_id"].strip(),
        "engagement_model": row["engagement_model"].strip(),
        "currency": row["currency"].strip().upper(),
        "source_provenance": {
            "source_type": (row.get("source_type") or "pilot_csv").strip() or "pilot_csv",
            "source_system": (row.get("source_system") or "pilot_commercial_sheet").strip() or "pilot_commercial_sheet",
            "source_record_id": (row.get("source_record_id") or commercial_id).strip() or commercial_id,
        },
    }

    if row.get("cost_rate", "").strip():
        record["cost_rate_usd"] = _parse_float(row["cost_rate"].strip(), "cost_rate", row_number)
    if row.get("bill_rate", "").strip():
        record["bill_rate_usd"] = _parse_float(row["bill_rate"].strip(), "bill_rate", row_number)
    if row.get("target_bill_rate", "").strip() and not row.get("bill_rate", "").strip():
        record["bill_rate_usd"] = _parse_float(row["target_bill_rate"].strip(), "target_bill_rate", row_number)

    for key in ["cost_rate_band", "bill_rate_band", "availability_note", "effective_from"]:
        value = _clean_optional(row, key)
        if value is not None:
            record[key] = value

    for column_name in OPTIONAL_FLOAT_COLUMNS:
        value = row.get(column_name, "").strip()
        if not value:
            continue
        if column_name in {"cost_rate", "bill_rate", "target_bill_rate"}:
            continue
        record[column_name] = _parse_float(value, column_name, row_number)

    for column_name in OPTIONAL_INT_COLUMNS:
        value = row.get(column_name, "").strip()
        if not value:
            continue
        parsed = _parse_int(value, column_name, row_number)
        if column_name == "availability_percent" and not 0 <= parsed <= 100:
            raise CsvImportError(f"Row {row_number}: availability_percent must be between 0 and 100.")
        record[column_name] = parsed

    return record


def import_pilot_commercial_csv(input_path: Path, output_path: Path) -> tuple[int, Path]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_required_columns(reader.fieldnames)

        records: list[dict] = []
        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(_row_to_commercial_record(row=row, row_number=index))

    if not records:
        raise CsvImportError("No importable data rows found. Add at least one populated row below the header.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=2)
        json_file.write("\n")

    return len(records), output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import pilot commercial-profile CSV into DynPro canonical commercial-profile JSON format.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to pilot commercial-profile CSV file.")
    parser.add_argument(
        "--output",
        default=Path("data/sample_json/commercial_profile.imported.json"),
        type=Path,
        help="Path to output JSON file (default: data/sample_json/commercial_profile.imported.json).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        count, output_path = import_pilot_commercial_csv(input_path=args.input, output_path=args.output)
    except CsvImportError as error:
        print(f"Pilot commercial-profile CSV import failed: {error}")
        return 1
    except FileNotFoundError:
        print(f"Pilot commercial-profile CSV import failed: file not found: {args.input}")
        return 1

    print(f"Imported {count} commercial-profile row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
