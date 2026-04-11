# Dashboard pogodowy Tatry

Interaktywny dashboard pogodowy dla obszaru Tatr zbudowany w `Streamlit`. Projekt laczy dane historyczne, dane biezace, forecast temperatur oraz modul AI do oceny ryzyka dla wskazanej lokalizacji lub trasy.

## O projekcie

Celem projektu jest polaczenie analizy danych pogodowych z praktycznym interfejsem, ktory pozwala:

- monitorowac warunki pogodowe na obszarze Tatr,
- przegladac dane historyczne i forecast,
- analizowac punkty siatki pogodowej na mapie,
- oceniac ryzyko wyprawy dla lokalizacji lub trasy,
- eksportowac dane do dalszej analizy.

Dashboard korzysta z najnowszego pliku forecast zapisanego w `data/json` i na jego podstawie buduje analize temperatur oraz ocene ryzyka. Dane moga byc odswiezane automatycznie przez GitHub Actions raz w tygodniu.

## Najwazniejsze funkcje

- Ocena ryzyka AI dla lokalizacji i tras w Tatrach.
- Rozpoznawanie miejsc i tras wpisywanych naturalnym jezykiem.
- Obsluga literowek i roznych form zapisu nazw lokalizacji.
- Wizualizacja trasy i punktow siatki prognozy na mapie.
- 24-godzinny wykres temperatur dla analizowanych punktow trasy.
- Widoki danych historycznych, forecastu i eksportu.
- Lokalna baza `SQLite` dla danych pogodowych.

## Jak dziala ocena ryzyka

1. Aplikacja laduje najnowszy plik forecast z katalogu `data/json`.
2. Uzytkownik wpisuje lokalizacje albo trase, np. `Morskie Oko` albo `z Zakopanego do Morskiego Oka`.
3. System probuje rozpoznac miejsca nalezace do obszaru Tatr.
4. Trasa jest mapowana na znane punkty i odcinki.
5. Dla najblizszych punktow siatki forecast generowany jest 24-godzinny przebieg temperatur.
6. Model AI zwraca ocene ryzyka i uzasadnienie po polsku.

Jesli wpisana lokalizacja nie nalezy do Tatr albo nie zostanie rozpoznana, dashboard nie pokazuje oceny ryzyka ani wykresu.

## Widoki dashboardu

- `Ocena ryzyka`
- `Dane historyczne`
- `Prognoza pogody`
- `Eksport danych`

## Tech Stack

- Python
- Streamlit
- Pandas
- Folium
- Altair
- SQLite
- OpenWeather API
- Meteostat API
- OpenAI SDK / OpenRouter

## Struktura projektu

```text
tatry-weather/
|-- .github/
|   `-- workflows/
|       `-- refresh-data.yml
|-- assets/
|   `-- grafika.png
|-- app.py
|-- ai_risk.py
|-- dashboard_utils.py
|-- dashboard_views.py
|-- spatial_config.py
|-- scripts/
|   |-- api_refresh.py
|   |-- cleanup_spatial_data.py
|   |-- cleanup_sqlite_bounds.py
|   |-- refresh_project.py
|   `-- weather_db.py
|-- data/
|   |-- weather_history.csv
|   |-- weather_history_for_eda.csv
|   `-- json/
|-- database/
|   |-- weather.db
|   `-- schema/
|-- notebooks/
|-- pyproject.toml
`-- uv.lock
```

## Uruchomienie lokalnie

### Wymagania

- Python `3.13+`
- `uv`

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/mbdlugosz/tatry-weather.git
cd tatry-weather
```

### 2. Instalacja zaleznosci

```bash
uv sync
```

### 3. Konfiguracja `.env`

Przykladowa konfiguracja:

```env
RAPIDAPI_KEY=your_rapidapi_key
OPENWEATHERAPI_KEY=your_openweather_key
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_RISK_MODEL=gpt-4o-mini
```

### 4. Uruchomienie dashboardu

```bash
uv run streamlit run app.py
```

## Automatyczne odswiezanie danych przez GitHub Actions

Repo zawiera workflow `.github/workflows/refresh-data.yml`, ktory:

- uruchamia sie automatycznie raz w tygodniu w niedziele o `03:00 UTC`,
- mozna go uruchomic recznie z zakladki `Actions`,
- czysci stare dane przestrzenne,
- pobiera nowe dane historyczne, biezace i forecast,
- aktualizuje `database/weather.db`,
- robi commit i push tylko wtedy, gdy dane rzeczywiscie sie zmienily.

### Jak skonfigurowac workflow

1. Wrzuc repozytorium na GitHub.
2. Wejdz w `Settings -> Secrets and variables -> Actions`.
3. W `Settings -> Actions -> General` upewnij sie, ze `Workflow permissions` pozwala na `Read and write permissions`.
4. Dodaj sekrety repo:

- `RAPIDAPI_KEY`
- `OPENWEATHERAPI_KEY`

5. Wejdz w zakladke `Actions`.
6. Otworz workflow `Refresh weather data`.
7. Kliknij `Run workflow`, aby sprawdzic pierwsze wykonanie.
8. Po poprawnym przebiegu GitHub bedzie odswiezal dane automatycznie co tydzien.

### Reczne odswiezanie lokalnie

```bash
uv run python scripts/refresh_project.py
```

Jesli chcesz zmienic gestosc siatki forecast albo zakres danych historycznych, edytuj argumenty wywolywane w `.github/workflows/refresh-data.yml` albo w `scripts/refresh_project.py`.

## Odswiezanie danych pojedynczym skryptem

```bash
uv run python scripts/api_refresh.py --mode all --import-to-db
```

Przydatne opcje:

- `--mode forecast`
- `--mode current`
- `--mode history`
- `--grid-size 10`
- `--history-start 2020-01-01`
- `--history-end 2025-01-01`

## Screenshoty

Mozesz dodac tutaj zrzuty ekranu z dashboardu, np.:

```md
![Ocena ryzyka](docs/screenshots/risk-dashboard.png)
![Prognoza pogody](docs/screenshots/forecast-dashboard.png)
```

## Ograniczenia

- Routing tras jest przyblizony i opiera sie na lokalnym grafie polaczen.
- Ocena ryzyka korzysta z najblizszych punktow siatki forecast, a nie z pelnego modelu terenowego.
- Jakosc wyniku zalezy od aktualnosci danych i gestosci siatki prognozy.

## Dalszy rozwoj

- dodanie wag czasowych do odcinkow tras,
- bardziej realistyczny routing tras tatrzanskich,
- rozszerzenie modelu ryzyka o kolejne parametry pogodowe,
- dalsze dopracowanie warstwy wizualnej dashboardu.
