CREATE TABLE IF NOT EXISTS weather_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temp REAL NOT NULL,
    feels_like REAL NOT NULL,
    pressure INTEGER NOT NULL,
    humidity INTEGER NOT NULL,
    pm10 REAL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    download_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (lat, lon, download_timestamp)
);
