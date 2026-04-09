# Dashboard pogodowy Tatry

Projekt analityczno-aplikacyjny dla obszaru Tatr. Repozytorium laczy pobieranie danych pogodowych z API, zapis danych do plikow `CSV` i `JSON`, lokalna baze `SQLite`, notebooki analityczne oraz dashboard w `Streamlit`.

Najwazniejsza czescia projektu jest obecnie dashboard, ktory pozwala:

- analizowac prognoze temperatur dla siatki punktow na obszarze Tatr,
- oceniac ryzyko wyprawy dla wskazanej lokalizacji lub trasy,
- wizualizowac trase i punkty siatki na mapie,
- przegladac dane historyczne i forecast,
- eksportowac dane do dalszej analizy.

## Funkcje

### 1. Dashboard Streamlit

Dashboard zawiera kilka widokow:

- `Ocena ryzyka`
- `Dane historyczne`
- `Prognoza pogody`
- `Eksport danych`

W module oceny ryzyka uzytkownik moze wpisac:

- pojedyncza lokalizacje, np. `Morskie Oko`,
- trase, np. `z Zakopanego do Morskiego Oka`,
- wpis z drobnymi literowkami lub odmieniona nazwa miejsca.

Aplikacja:

- rozpoznaje miejsca nalezace do obszaru Tatr,
- wybiera najnowszy plik forecast z katalogu `data/json`,
- dopasowuje punkty siatki prognozy do analizowanej lokalizacji lub trasy,
- pokazuje trase na mapie,
- generuje 24-godzinna ocene ryzyka przy pomocy modelu AI,
- rysuje wykres temperatur dla punktow startowych, koncowych i posrednich.

Jesli wpisana lokalizacja nie nalezy do Tatr albo nie zostanie rozpoznana, dashboard nie pokazuje oceny ryzyka ani wykresu.

### 2. Dane historyczne

Projekt pobiera dane historyczne dla wybranych stacji Meteostat i zapisuje je do pliku:

- `data/weather_history_for_eda.csv`

Te dane sa wykorzystywane glownie w notebookach i analizie eksploracyjnej.

### 3. Dane biezace i forecast

Projekt pobiera dane z OpenWeather dla siatki punktow w granicach zdefiniowanego obszaru Tatr:

- dane biezace trafiaja do `data/weather_history.csv`,
- forecast zapisywany jest do plikow `JSON` w `data/json/`.

Rozdzielczosc siatki mozna kontrolowac parametrem `--grid-size`.

### 4. SQLite

Aktualne dane pogodowe moga byc importowane do lokalnej bazy:

- `database/weather.db`

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

## Technologie

- Python 3.13+
- Streamlit
- Pandas
- Folium
- Altair
- SQLite
- OpenWeather API
- Meteostat API przez RapidAPI
- OpenRouter / OpenAI SDK do oceny ryzyka AI

## Wymagania

- Python `3.13+`
- `uv`

## Instalacja

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

Przyklad:

```env
RAPIDAPI_KEY=your_rapidapi_key
OPENWEATHERAPI_KEY=your_openweather_key
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_RISK_MODEL=gpt-4o-mini
```

Minimalnie:

- `RAPIDAPI_KEY` jest potrzebny do danych historycznych,
- `OPENWEATHERAPI_KEY` jest potrzebny do danych biezacych i forecast,
- `OPENROUTER_API_KEY` jest potrzebny do oceny ryzyka AI.

## Uruchomienie dashboardu

```bash
uv run streamlit run app.py
```

Po uruchomieniu aplikacja przekierowuje domyslnie do strony `Ocena ryzyka`.

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

### Wszystko naraz

```bash
uv run python scripts/api_refresh.py --mode all
```

### Zmiana gestosci siatki

```bash
uv run python scripts/api_refresh.py --mode forecast --grid-size 10
```

Im wiekszy `grid-size`, tym wiecej punktow analizowanych na mapie i dokladniejsze dopasowanie lokalizacji do siatki forecast.

### Import danych do SQLite

```bash
uv run python scripts/api_refresh.py --mode current --import-to-db
```

Lub osobno:

```bash
uv run python scripts/import_weather_history.py
```

## Notebooki

Notebooki mozna uruchomic przez:

```bash
uv run jupyter lab
```

Repozytorium zawiera m.in. materialy do:

- analizy EDA,
- eksperymentow z API,
- testowania odpowiedzi AI dla oceny ryzyka.

## Jak dziala ocena ryzyka

1. Dashboard laduje najnowszy plik forecast z `data/json`.
2. Uzytkownik wpisuje lokalizacje albo trase.
3. System probuje rozpoznac punkty nalezace do Tatr.
4. Dla rozpoznanej lokalizacji lub trasy wybierane sa najblizsze punkty siatki forecast.
5. Model AI generuje ocene ryzyka: `safe`, `risky` albo `dangerous`.
6. Wynik jest prezentowany jako opis po polsku wraz z mapa i wykresem temperatur dla 24 godzin.

## Ograniczenia

- Routing trasy jest przyblizony i opiera sie na lokalnym grafie polaczen oraz szablonach tras, a nie na pelnym silniku szlakowym.
- Ocena ryzyka korzysta z punktow siatki forecast, a nie z idealnie dowolnych wspolrzednych w terenie.
- Jakosc oceny zalezy od aktualnosci danych API i gestosci siatki forecast.

## Rozwoj projektu

Planowane lub mozliwe dalsze rozszerzenia:

- dodanie wag czasowych do odcinkow tras i wyboru najbardziej realistycznej trasy,
- rozszerzenie katalogu punktow i tras tatrzanskich,
- rozbudowa modelu ryzyka o wiecej parametrow pogodowych niz temperatura,
- lepszy eksport danych i wynikow analiz,
- dalsze dopracowanie warstwy prezentacyjnej dashboardu.
