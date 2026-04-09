# Dashboard pogodowy Tatry

Interaktywny dashboard pogodowy dla obszaru Tatr zbudowany w `Streamlit`. Projekt laczy dane historyczne, dane biezace, forecast temperatur oraz modul AI do oceny ryzyka dla wskazanej lokalizacji lub trasy.

## O projekcie

Celem projektu jest polaczenie analizy danych pogodowych z praktycznym interfejsem, ktory pozwala:

- monitorowac warunki pogodowe na obszarze Tatr,
- przegladac dane historyczne i forecast,
- analizowac punkty siatki pogodowej na mapie,
- oceniac ryzyko wyprawy dla lokalizacji lub trasy,
- eksportowac dane do dalszej analizy.

Dashboard korzysta z najnowszego pliku forecast zapisanego w `data/json` i na jego podstawie buduje analize temperatur oraz ocene ryzyka.

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
|-- app.py
|-- ai_risk.py
|-- dashboard_utils.py
|-- spatial_config.py
|-- pages/
|   |-- 0_Ocena_ryzyka.py
|   |-- 1_Dane_historyczne.py
|   |-- 2_Prognoza_pogody.py
|   `-- 3_Eksport_danych.py
|-- scripts/
|   |-- api_refresh.py
|   |-- import_weather_history.py
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

## Odswiezanie danych

### Forecast

```bash
uv run python scripts/api_refresh.py --mode forecast
```

### Dane biezace

```bash
uv run python scripts/api_refresh.py --mode current
```

### Dane historyczne

```bash
uv run python scripts/api_refresh.py --mode history
```

### Wszystkie dane

```bash
uv run python scripts/api_refresh.py --mode all
```

### Zmiana gestosci siatki forecast

```bash
uv run python scripts/api_refresh.py --mode forecast --grid-size 10
```

Im wiekszy `grid-size`, tym wiecej punktow siatki i dokladniejsze dopasowanie lokalizacji do prognozy.

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
