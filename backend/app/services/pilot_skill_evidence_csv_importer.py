from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_COLUMNS = [
    "skill_evidence_id",
    "person_id",
    "skill",
    "source",
    "confidence",
]

FLOAT_COLUMNS = {"confidence"}
LIST_COLUMNS = {"workflow_tags"}

DEFAULT_WORKFLOW_TAGS = ["expert_finder", "interviewer_finder", "pod_builder"]


class CsvImportError(ValueError):
    """Raised when pilot skill-evidence CSV cannot be converted into canonical JSON records."""


def _parse_float(value: str, column_name: str, row_number: int) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise CsvImportError(
            f"Row {row_number}: column '{column_name}' must be numeric, got '{value}'."
        ) from exc


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
            f"{readable}. Check README for the skill-evidence intake template column list."
        )


def _validate_required_values(row: dict[str, str], row_number: int) -> None:
    missing_values = [column for column in REQUIRED_COLUMNS if not row.get(column, "").strip()]
    if missing_values:
        readable = ", ".join(missing_values)
        raise CsvImportError(
            f"Row {row_number}: missing required value(s): {readable}. "
            "Please fill skill_evidence_id, person_id, skill, source, and confidence before importing."
        )


def _row_to_skill_evidence_record(row: dict[str, str], row_number: int) -> dict:
    _validate_required_values(row=row, row_number=row_number)

    workflow_tags = _parse_list(row.get("workflow_tags", ""))
    if not workflow_tags:
        workflow_tags = DEFAULT_WORKFLOW_TAGS

    confidence = _parse_float(value=row["confidence"].strip(), column_name="confidence", row_number=row_number)

    record: dict[str, object] = {
        "evidence_id": row["skill_evidence_id"].strip(),
        "person_id": row["person_id"].strip(),
        "skill_name": row["skill"].strip(),
        "evidence_text": _clean_optional(row=row, key="evidence_text")
        or f"Pilot skill evidence for {row['skill'].strip()}.",
        "source_uri": row["source"].strip(),
        "confidence": confidence,
        "metadata": {
            "workflow_tags": workflow_tags,
            "validated_by": _clean_optional(row=row, key="validated_by") or "pilot_import",
        },
    }

    for key in ["observed_at"]:
        value = _clean_optional(row=row, key=key)
        if value is not None:
            record[key] = value

    return record


def import_pilot_skill_evidence_csv(input_path: Path, output_path: Path) -> tuple[int, Path]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_required_columns(reader.fieldnames)

        records: list[dict] = []
        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(_row_to_skill_evidence_record(row=row, row_number=index))

    if not records:
        raise CsvImportError("No importable data rows found. Add at least one populated row below the header.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=2)
        json_file.write("\n")

    return len(records), output_path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import pilot skill-evidence CSV into DynPro canonical skill_evidence JSON format.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to pilot skill-evidence CSV file.",
    )
    parser.add_argument(
        "--output",
        default=Path("data/sample_json/skill_evidence.imported.json"),
        type=Path,
        help="Path to output JSON file (default: data/sample_json/skill_evidence.imported.json).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    try:
        count, output_path = import_pilot_skill_evidence_csv(input_path=args.input, output_path=args.output)
    except CsvImportError as error:
        print(f"Pilot skill-evidence CSV import failed: {error}")
        return 1
    except FileNotFoundError:
        print(f"Pilot skill-evidence CSV import failed: file not found: {args.input}")
        return 1

    print(f"Imported {count} skill-evidence row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
