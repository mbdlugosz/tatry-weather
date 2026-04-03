from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from spatial_config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN

DATABASE_PATH = BASE_DIR / "database" / "weather.db"


def cleanup_weather_history(db_path: Path = DATABASE_PATH) -> tuple[int, int]:
    connection = sqlite3.connect(db_path)
    try:
        before_count = int(
            connection.execute("SELECT COUNT(*) FROM weather_history").fetchone()[0]
        )
        connection.execute(
            """
            DELETE FROM weather_history
            WHERE lat < ?
               OR lat > ?
               OR lon < ?
               OR lon > ?
            """,
            (LAT_MIN, LAT_MAX, LON_MIN, LON_MAX),
        )
        connection.commit()
        after_count = int(
            connection.execute("SELECT COUNT(*) FROM weather_history").fetchone()[0]
        )
    finally:
        connection.close()

    return before_count, after_count


def main() -> None:
    before_count, after_count = cleanup_weather_history()
    print(f"Rows before cleanup: {before_count}")
    print(f"Rows after cleanup: {after_count}")
    print(f"Rows removed: {before_count - after_count}")


if __name__ == "__main__":
    main()
