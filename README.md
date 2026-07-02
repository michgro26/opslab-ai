# OpsLab AI

OpsLab AI to lokalna aplikacja demonstracyjna do analizy danych operacyjnych, oceny ryzyka i prostych automatyzacji zadań IT.

Projekt nie korzysta z prawdziwych danych. Przy uruchomieniu tworzy lokalną bazę SQLite i uzupełnia ją danymi testowymi: użytkownikami, urządzeniami, zadaniami, logami i raportami.

Celem projektu było pokazanie, jak można połączyć analizę danych, prostego agenta narzędziowego, dashboard i opcjonalny lokalny LLM w jednej aplikacji.

## Co robi aplikacja

OpsLab AI pozwala:

- analizować jakość danych użytkowników,
- sprawdzać urządzenia wymagające uwagi,
- wykrywać zadania po terminie,
- liczyć risk score dla danych operacyjnych,
- generować plan automatyzacji,
- symulować podnoszenie priorytetów zadań po terminie,
- zapisywać logi działań i raporty agenta,
- opcjonalnie używać lokalnego LLM przez Ollama do redagowania końcowych rekomendacji.

Aplikacja ma działać jako sandbox, więc nie wymaga dostępu do żadnych firmowych systemów, API ani zewnętrznej bazy danych.

## Główne widoki

### Dashboard

Główny panel pokazuje ogólny stan danych demonstracyjnych:

- liczba użytkowników,
- liczba urządzeń,
- liczba zadań,
- problemy jakości danych,
- urządzenia wymagające uwagi,
- zadania po terminie,
- risk score z kolorowym oznaczeniem poziomu ryzyka.

### Agent AI

Agent przyjmuje polecenie tekstowe i dobiera odpowiednie narzędzia. Nie jest to tylko formularz z gotowymi przyciskami — agent rozpoznaje intencję na podstawie wpisanego tekstu.

Przykładowe polecenia:

```text
Znajdź problemy jakości danych użytkowników
```

```text
Sprawdź urządzenia wymagające aktualizacji
```

```text
Pokaż procesy po terminie i zaproponuj automatyzację
```

```text
Uruchom automatyzację priorytetów dla zadań po terminie
```

```text
Zrób audyt ryzyk operacyjnych i wskaż priorytety
```

Po uruchomieniu agent pokazuje:

- odpowiedź dla użytkownika,
- listę użytych narzędzi,
- surowe wyniki w formacie JSON.

### Audyt ryzyka

Zakładka audytu pokazuje syntetyczną ocenę ryzyka operacyjnego. Wynik jest liczony na podstawie kilku obszarów:

- zadania po terminie,
- średni czas opóźnienia,
- urządzenia wymagające uwagi,
- problemy jakości danych.

Kolory są użyte jako sygnał, a nie dekoracja:

- zielony — niskie ryzyko,
- żółty — średnie ryzyko,
- czerwony — wysokie ryzyko.

Z tego widoku można pobrać raport w Markdown.

### Dane

Zakładka z podglądem danych testowych. Można podejrzeć użytkowników, urządzenia i zadania, na których pracują narzędzia analityczne.

### Logi i raporty

Tutaj zapisują się działania systemu, np. wygenerowanie danych, uruchomienie automatyzacji albo raport agenta.

## Jak działa agent

Agent działa w dwóch krokach.

Najpierw zwykły kod w Pythonie wykonuje analizę danych. To on liczy metryki, sprawdza rekordy i wykonuje automatyzacje. LLM nie zgaduje wyników i nie odpytuje bazy samodzielnie.

Potem, jeśli tryb LLM jest włączony, wyniki narzędzi są wysyłane do lokalnego modelu przez Ollama. Model dostaje gotowy JSON i redaguje bardziej naturalny raport.

Przepływ wygląda tak:

```text
polecenie użytkownika
→ wybór narzędzi
→ analiza danych w Pythonie
→ wyniki JSON
→ opcjonalny lokalny LLM
→ raport i rekomendacje
→ zapis do SQLite
```

Jeśli Ollama nie działa albo model odpowiada zbyt długo, aplikacja wraca do trybu podstawowego i nadal pokazuje wynik z narzędzi.

## Tryb LLM

Tryb LLM jest opcjonalny. Projekt działa bez niego.

Po włączeniu LLM aplikacja korzysta z lokalnej Ollamy, domyślnie z modelu:

```text
llama3.2
```

Na słabszym sprzęcie lepiej użyć lżejszego modelu:

```text
llama3.2:1b
```

Pobranie modelu:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull llama3.2:1b
```

Sprawdzenie modeli:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

W aplikacji model można zmienić w sidebarze, w polu `Model Ollama`.

## Technologie które użyłem

- Python
- Streamlit
- SQLite
- SQLAlchemy
- Pandas
- FastAPI
- Ollama jako opcjonalny lokalny LLM
- pytest

## Uruchomienie (WIN)

Przejdź do folderu projektu:

```powershell
cd D:\CSI\opslab-ai\opslab-ai
```

Uruchom aplikację:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8502
```

Aplikacja będzie dostępna pod adresem:

```text
http://127.0.0.1:8502
```

## Dodałem możliwość uruchamiania plikiem BAT

Można utworzyć plik:

```text
start_opslab.bat
```

Z zawartością:

```bat
@echo off
cd /d D:\CSI\opslab-ai\opslab-ai

echo Uruchamianie OpsLab AI...
echo.

start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8502"

.\.venv\Scripts\python.exe -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8502

pause
```

Po tym aplikację można uruchamiać dwuklikiem.

## API FastAPI

Projekt ma też prosty backend FastAPI.

Uruchomienie:

```bash
uvicorn app.main:app --reload
```

Endpointy:

```text
GET  /health
GET  /summary
POST /agent
```

Przykład:

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Sprawdź urządzenia wymagające aktualizacji"}'
```

## Struktura projektu

```text
opslab-ai/
├── app/
│   ├── agent.py
│   ├── analytics.py
│   ├── database.py
│   ├── demo_data.py
│   ├── llm_client.py
│   ├── main.py
│   ├── models.py
│   └── tools.py
├── dashboard/
│   └── streamlit_app.py
├── tests/
├── data/
├── Dockerfile
├── requirements.txt
└── README.md
```

## Co ten projekt pokazuje

- praca z lokalną bazą danych,
- analiza danych operacyjnych,
- wykrywanie problemów jakości danych,
- prosty mechanizm agenta narzędziowego,
- opcjonalne użycie LLM do redagowania raportów,
- dashboard z metrykami i wykresami,
- logowanie działań,
- podejście demo bez ryzyka użycia prawdziwych danych.

