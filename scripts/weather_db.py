from __future__ import annotations

import csv
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = BASE_DIR / "database"
SCHEMA_PATH = DATABASE_DIR / "schema" / "create_weather_history.sql"
DEFAULT_DB_PATH = DATABASE_DIR / "weather.db"
DEFAULT_CSV_PATH = BASE_DIR / "data" / "weather_history.csv"


@dataclass(slots=True)
class WeatherHistoryRecord:
    temp: float
    feels_like: float
    pressure: int
    humidity: int
    pm10: float | None
    lat: float
    lon: float
    download_timestamp: str


class WeatherHistoryRepository:
    UNIQUE_INDEX_SQL = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_history_unique_record
        ON weather_history (lat, lon, download_timestamp)
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_table(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as connection:
            connection.executescript(schema)
            connection.execute(self.UNIQUE_INDEX_SQL)

    def add_record(self, record: WeatherHistoryRecord) -> int:
        query = """
            INSERT OR IGNORE INTO weather_history (
                temp,
                feels_like,
                pressure,
                humidity,
                pm10,
                lat,
                lon,
                download_timestamp
            )
            VALUES (
                :temp,
                :feels_like,
                :pressure,
                :humidity,
                :pm10,
                :lat,
                :lon,
                :download_timestamp
            )
        """
        with self._connect() as connection:
            cursor = connection.execute(query, asdict(record))
            connection.commit()
            return int(cursor.lastrowid)

    def get_all_records(self) -> list[dict]:
        query = """
            SELECT
                id,
                temp,
                feels_like,
                pressure,
                humidity,
                pm10,
                lat,
                lon,
                download_timestamp,
                created_at
            FROM weather_history
            ORDER BY download_timestamp DESC, id DESC
        """
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()
        return [dict(row) for row in rows]

    def get_record_count(self) -> int:
        query = "SELECT COUNT(*) FROM weather_history"
        with self._connect() as connection:
            return int(connection.execute(query).fetchone()[0])


def import_weather_history_csv(
    csv_path: str | Path = DEFAULT_CSV_PATH,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> tuple[int, int]:
    repository = WeatherHistoryRepository(db_path)
    repository.create_table()
    before_count = repository.get_record_count()

    with Path(csv_path).open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        total_rows = 0
        for row in reader:
            repository.add_record(
                WeatherHistoryRecord(
                    temp=float(row["temp"]),
                    feels_like=float(row["feels_like"]),
                    pressure=int(row["pressure"]),
                    humidity=int(row["humidity"]),
                    pm10=float(row["pm10"]) if row["pm10"] else None,
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    download_timestamp=row["download_timestamp"],
                )
            )
            total_rows += 1

    after_count = repository.get_record_count()
    inserted_count = after_count - before_count
    skipped_count = total_rows - inserted_count
    return inserted_count, skipped_count


if __name__ == "__main__":
    repository = WeatherHistoryRepository()
    repository.create_table()
    print(f"Database ready: {repository.db_path}")
