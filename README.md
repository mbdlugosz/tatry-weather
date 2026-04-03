# Tatry Weather

Projekt pogodowy dla Tatr oparty o dane z API, notebooki analityczne oraz lokalną bazę `SQLite`.

## Opis

Repozytorium łączy trzy warstwy:

- pobieranie danych pogodowych z zewnętrznych API,
- zapis danych do plików `CSV` i `JSON`,
- zapis aktualnych danych z pliku `data/weather_history.csv` do bazy `SQLite`.

W projekcie występują dwa główne zbiory danych:

- `data/weather_history.csv` - aktualne dane pogodowe z siatki punktów w regionie Tatr,
- `data/weather_history_for_eda.csv` - osobny zbiór danych historycznych używany do analizy w notebooku EDA.

Baza `database/weather.db` jest obecnie budowana na podstawie pliku `data/weather_history.csv`.

## Funkcje

- pobieranie historycznych danych pogodowych z Meteostat przez RapidAPI,
- pobieranie aktualnych danych pogodowych z OpenWeather,
- pobieranie prognozy i zapis do `JSON`,
- zapis aktualnych danych do `SQLite`,
- odczyt danych z bazy w notebooku,
- eksploracyjna analiza danych historycznych w notebooku `EDA.ipynb`.

## Struktura projektu

```text
tatry-weather/
├── API .ipynb
├── EDA.ipynb
├── data/
│   ├── weather_history.csv
│   ├── weather_history_for_eda.csv
│   └── json/
├── database/
│   ├── weather.db
│   └── schema/
├── notebooks/
│   └── SQLite_DB.ipynb
├── scripts/
│   ├── api_refresh.py
│   ├── import_weather_history.py
│   └── weather_db.py
├── pyproject.toml
└── uv.lock
```

## Instalacja

### Wymagania

- Python `3.13+`
- `uv`

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/mbdlugosz/tatry-weather.git
cd tatry-weather
```

### 2. Zainstaluj zależności

```bash
uv sync
```

### 3. Skonfiguruj `.env`

```env
RAPIDAPI_KEY=your_rapidapi_key
OPENWEATHERAPI_KEY=your_openweather_key
```

## Uruchomienie

### Notebooki

```bash
uv run jupyter lab
```

Notebooki:

- `API .ipynb` - pobieranie danych z API,
- `EDA.ipynb` - analiza historyczna,
- `notebooks/SQLite_DB.ipynb` - odczyt danych z `database/weather.db`.

### Skrypty

Utworzenie bazy:

```bash
python scripts\weather_db.py
```

Import `data/weather_history.csv` do SQLite:

```bash
python scripts\import_weather_history.py
```

Odświeżenie danych z API:

```bash
uv run python scripts\api_refresh.py --mode current
```

Odświeżenie danych z API i import do bazy:

```bash
uv run python scripts\api_refresh.py --mode current --import-to-db
```

## Baza danych

Aktualna tabela `weather_history` w `database/weather.db` zawiera kolumny:

- `temp`
- `feels_like`
- `pressure`
- `humidity`
- `pm10`
- `lat`
- `lon`
- `download_timestamp`
- `created_at`

Schemat znajduje się w:

- `database/schema/create_weather_history.sql`

## Work in Progress

Projekt jest nadal rozwijany. Aktualnie trwają prace nad:

- uporządkowaniem pipeline'u danych,
- dalszą integracją warstwy bazy danych,
- rozwojem dashboardu prezentującego dane pogodowe.

## Planowany dashboard w Streamlit

W kolejnym etapie projektu planowany jest dashboard w `Streamlit`, który pokaże:

- aktualną pogodę na obszarze Tatr,
- mapę punktów siatki pogodowej,
- podgląd parametrów takich jak temperatura, wilgotność i PM10,
- prostą eksplorację danych historycznych i bieżących.
