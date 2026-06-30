# OpsLab AI

**OpsLab AI** to demonstracyjny agent AI do analizy danych operacyjnych, wykrywania problemów jakości danych oraz automatyzacji zadań IT. Projekt działa w pełni lokalnie na syntetycznych danych generowanych automatycznie.

Projekt nie używa danych produkcyjnych, nie wymaga dostępu do firmowych systemów i nie wymaga zakładania zewnętrznej bazy danych.

## Co pokazuje projekt

- wykorzystanie Pythona w analizie i automatyzacji procesów,
- prosty agent AI z mechanizmem wyboru narzędzi,
- analizę danych użytkowników, urządzeń i zadań operacyjnych,
- automatyczne generowanie rekomendacji,
- dashboard w Streamlit,
- lokalną bazę SQLite,
- API w FastAPI,
- testy jednostkowe w pytest,
- projekt gotowy do uruchomienia w Dockerze.

## Dane demonstracyjne

Przy pierwszym uruchomieniu projekt tworzy lokalną bazę:

```text
data/opslab_ai.db
```

W bazie znajdują się syntetyczne dane:

- użytkownicy,
- urządzenia,
- zadania operacyjne,
- logi automatyzacji,
- raporty AI.

Generator celowo dodaje przykładowe problemy: brakujące e-maile, brak działu, duplikaty, stare wersje BIOS, niewspierane wersje systemu, zadania po terminie.

## Szybki start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.demo_data --reset
streamlit run dashboard/streamlit_app.py
```

Aplikacja Streamlit uruchomi się domyślnie pod adresem:

```text
http://localhost:8501
```

## API FastAPI

```bash
uvicorn app.main:app --reload
```

Endpointy:

```text
GET  /health
GET  /summary
POST /agent
```

Przykładowe zapytanie:

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Sprawdź urządzenia wymagające aktualizacji"}'
```

## Docker

```bash
docker build -t opslab-ai .
docker run -p 8501:8501 opslab-ai
```

## Przykładowe polecenia dla agenta

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

## Struktura projektu

```text
opslab-ai/
├── app/
│   ├── agent.py
│   ├── analytics.py
│   ├── database.py
│   ├── demo_data.py
│   ├── main.py
│   ├── models.py
│   └── tools.py
├── dashboard/
│   └── streamlit_app.py
├── tests/
│   ├── test_agent.py
│   ├── test_analytics.py
│   └── test_tools.py
├── data/
├── Dockerfile
├── requirements.txt
└── README.md
```

## Testy

```bash
pytest
```

## Uwaga

Obecna wersja używa deterministycznego agenta demonstracyjnego, który nie wymaga klucza API do modelu językowego. Dzięki temu projekt można uruchomić od razu lokalnie. 
