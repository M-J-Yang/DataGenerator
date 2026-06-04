import argparse
import csv
from pathlib import Path


REQUIRED_COLUMNS = ("key", "target")


def validate_csv(csv_path: Path) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"CSV path is not a file: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        missing_columns = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
        if missing_columns:
            raise ValueError(f"CSV missing required columns: {', '.join(missing_columns)}")

        row_count = 0
        empty_target_rows = []
        empty_key_rows = []
        duplicate_keys = []
        seen_keys = set()

        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            key = (row.get("key") or "").strip()
            target = (row.get("target") or "").strip()

            if not key:
                empty_key_rows.append(line_number)
            elif key in seen_keys:
                duplicate_keys.append(key)
            else:
                seen_keys.add(key)

            if not target:
                empty_target_rows.append(line_number)

        if row_count == 0:
            raise ValueError("CSV has no data rows")
        if empty_key_rows:
            raise ValueError(f"CSV has empty key values on lines: {format_limited(empty_key_rows)}")
        if empty_target_rows:
            raise ValueError(f"CSV has empty target values on lines: {format_limited(empty_target_rows)}")
        if duplicate_keys:
            raise ValueError(f"CSV has duplicate key values: {format_limited(duplicate_keys)}")

    return row_count


def format_limited(values: list[object], limit: int = 10) -> str:
    shown = ", ".join(str(value) for value in values[:limit])
    if len(values) > limit:
        return f"{shown}, ... ({len(values)} total)"
    return shown


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate cleaned_transcripts.csv for TTS generation.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="cleaned_transcripts.csv",
        help="Input CSV path, default: cleaned_transcripts.csv",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    row_count = validate_csv(csv_path)
    print(f"OK: {csv_path} contains {row_count} valid rows with key and target columns.")


if __name__ == "__main__":
    main()
