# Dashboard pogodowy Tatry

Prosty dashboard w `Streamlit`, ktory pokazuje pogode dla obszaru Tatr i pomaga ocenic warunki przed wyjsciem w gory.

## Co robi dashboard

Dashboard pozwala:

- sprawdzic ocene ryzyka dla miejsca albo trasy w Tatrach,
- zobaczyc mape lokalizacji i przebieg temperatur,
- przejrzec dane historyczne,
- przejrzec aktualna prognoze,
- pobrac dane do pliku CSV, Excel lub JSON.

## Jak dziala

Dashboard korzysta z zapisanych danych pogodowych znajdujacych sie w repozytorium:

- `data/json` zawiera prognozy,
- `data/weather_history.csv` zawiera dane pogodowe,
- `database/weather.db` zawiera lokalna baze danych.

W widoku `Ocena ryzyka` wpisujesz nazwe miejsca albo trase, a aplikacja dopasowuje opis do danych pogodowych i pokazuje wynik wraz z uzasadnieniem.

## Uruchomienie lokalnie

### Wymagania

- Python `3.13`
- `uv`

### 1. Pobierz repozytorium

```bash
git clone https://github.com/mbdlugosz/tatry-weather.git
cd tatry-weather
```

### 2. Zainstaluj zaleznosci

```bash
uv sync
```

### 3. Dodaj plik `.env`

Utworz plik `.env` w katalogu projektu.

Jesli chcesz korzystac z oceny ryzyka AI, dodaj:

```env
OPENROUTER_API_KEY=twoj_klucz
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_RISK_MODEL=gpt-4o-mini
```

Jesli chcesz dodatkowo odswiezac dane lokalnie skryptami, dodaj takze:

```env
RAPIDAPI_KEY=twoj_rapidapi_key
OPENWEATHERAPI_KEY=twoj_openweather_key
```

### 4. Uruchom dashboard

```bash
uv run streamlit run app.py
```

Po uruchomieniu otworz adres pokazany w terminalu, zwykle:

`http://localhost:8501`

## Automatyczne odswiezanie danych

Repo zawiera workflow GitHub Actions:

`.github/workflows/refresh-data.yml`

Workflow:

- uruchamia sie raz w tygodniu,
- pobiera nowe dane pogodowe,
- aktualizuje pliki w repo,
- zapisuje zmiany automatycznie tylko wtedy, gdy dane sie zmienily.

Do dzialania workflow potrzebne sa sekrety repozytorium GitHub:

- `RAPIDAPI_KEY`
- `OPENWEATHERAPI_KEY`

## Najwazniejsze pliki

- `app.py` - uruchamia dashboard
- `dashboard_views.py` - widoki dashboardu
- `dashboard_utils.py` - wspolne funkcje i styl
- `ai_risk.py` - logika oceny ryzyka AI
- `scripts/` - skrypty do odswiezania danych

