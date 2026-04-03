from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from spatial_config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, is_inside_bounds

DATA_DIR = BASE_DIR / "data"
JSON_DIR = DATA_DIR / "json"
CSV_PATH = DATA_DIR / "weather_history.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Czyszczenie plikow CSV i JSON spoza aktualnego obszaru Tatr."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pokaz podsumowanie bez zapisywania zmian.",
    )
    return parser.parse_args()



def clean_csv(csv_path: Path, *, dry_run: bool) -> tuple[int, int]:
    if not csv_path.exists():
        return 0, 0

    df = pd.read_csv(csv_path)
    mask = df["lat"].between(LAT_MIN, LAT_MAX) & df["lon"].between(LON_MIN, LON_MAX)
    kept_count = int(mask.sum())
    removed_count = int((~mask).sum())

    if not dry_run:
        df.loc[mask].to_csv(csv_path, index=False)

    return kept_count, removed_count


def clean_json_files(json_dir: Path, *, dry_run: bool) -> tuple[int, int]:
    removed_files = 0
    kept_files = 0

    for path in sorted(json_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        is_valid = all(is_inside_bounds(float(item["lat"]), float(item["lon"])) for item in data)
        if is_valid:
            kept_files += 1
            continue

        removed_files += 1
        if not dry_run:
            path.unlink()

    return kept_files, removed_files


def main() -> None:
    args = parse_args()

    csv_kept, csv_removed = clean_csv(CSV_PATH, dry_run=args.dry_run)
    json_kept, json_removed = clean_json_files(JSON_DIR, dry_run=args.dry_run)

    print(f"CSV kept rows: {csv_kept}")
    print(f"CSV removed rows: {csv_removed}")
    print(f"JSON kept files: {json_kept}")
    print(f"JSON removed files: {json_removed}")


if __name__ == "__main__":
    main()
