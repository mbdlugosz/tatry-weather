# Tatry Weather

Projekt analityczno-pogodowy poświęcony warunkom atmosferycznym w rejonie Tatr. Repozytorium łączy pobieranie danych pogodowych z zewnętrznych API, zapis danych do plików oraz eksploracyjną analizę danych historycznych w notebookach Jupyter.

## Opis

Celem projektu jest budowa aplikacji pogodowej dla Tatr, która w czytelny sposób pokaże aktualne warunki, dane historyczne i dalsze możliwości analizy. Obecnie repozytorium koncentruje się na dwóch obszarach:

- pobieraniu danych pogodowych z API,
- analizie historycznych danych pogodowych dla regionu Tatr.

Projekt stanowi bazę pod dalszy rozwój aplikacji, w tym dashboardu w Streamlit.

## Funkcje

- pobieranie historycznych danych pogodowych z Meteostat przez RapidAPI,
- pobieranie aktualnych danych pogodowych z OpenWeather,
- zapis danych do formatów `CSV` i `JSON`,
- eksploracyjna analiza danych pogodowych w notebooku `EDA.ipynb`,
- analiza temperatury, wiatru i opadów dla wybranych lokalizacji w regionie Tatr,
- przygotowana struktura danych pod dalszy rozwój aplikacji i warstwy wizualnej.

## Struktura projektu

```text
tatry-weather/
├── API .ipynb
├── EDA.ipynb
├── data/
│   ├── weather_history.csv
│   ├── weather_history_for_eda.csv
│   └── json/
├── pyproject.toml
└── uv.lock
```

## Instalacja

### Wymagania

- Python `3.13+`
- `uv` lub standardowe środowisko wirtualne dla Pythona

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/mbdlugosz/tatry-weather.git
cd tatry-weather
```

### 2. Zainstaluj zależności

Rekomendowana opcja z użyciem `uv`:

```bash
uv sync
```

### 3. Skonfiguruj zmienne środowiskowe

Utwórz plik `.env` w katalogu głównym projektu i dodaj:

```env
RAPIDAPI_KEY=your_rapidapi_key
OPENWEATHERAPI_KEY=your_openweather_key
```

## Uruchomienie

Projekt jest obecnie rozwijany głównie w formie notebooków Jupyter.

### Uruchomienie środowiska Jupyter

```bash
uv run jupyter lab
```

Następnie otwórz:

- `API .ipynb` - pobieranie danych z API i zapis wyników,
- `EDA.ipynb` - analiza eksploracyjna danych historycznych.

## Work in Progress

Projekt jest w trakcie rozwoju. Aktualny zakres obejmuje:

- integrację z zewnętrznymi źródłami danych pogodowych,
- zapis i porządkowanie danych wejściowych,
- analizę historycznych danych pogodowych dla regionu Tatr,
- przygotowanie podstaw pod warstwę prezentacyjną.

Najbliższe kierunki rozwoju:

- uporządkowanie pipeline'u pobierania danych,
- dodanie skryptów uruchamianych poza notebookami,
- rozszerzenie analizy o kolejne wskaźniki pogodowe,
- budowa dashboardu do prezentacji wyników.

## Planowany dashboard w Streamlit

W kolejnym etapie projektu planowane jest przygotowanie interaktywnego dashboardu w `Streamlit`, który pozwoli na:

- podgląd aktualnej pogody w wybranych punktach Tatr,
- prezentację danych historycznych na wykresach,
- porównywanie lokalizacji i warunków pogodowych,
- filtrowanie danych po dacie, parametrze i obszarze,
- udostępnienie projektu w bardziej przystępnej formie niż notebooki.

Docelowo dashboard ma pełnić rolę lekkiej aplikacji analitycznej i prezentacyjnej dla danych pogodowych związanych z Tatrami.

## Technologie

- Python
- JupyterLab
- pandas
- matplotlib
- seaborn
- tqdm
- python-dotenv

## Status

Repozytorium przedstawia aktualny etap budowy aplikacji pogodowej dla Tatr: od pozyskiwania danych, przez ich zapis, po wstępną analizę i przygotowanie pod dashboard.
