from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def is_llm_enabled() -> bool:
    return os.getenv("OPSLAB_USE_LLM", "false").lower() in {"1", "true", "yes", "on"}


def generate_llm_report(
    user_prompt: str,
    tools_used: list[str],
    raw_results: dict[str, Any],
    deterministic_summary: str,
) -> dict[str, Any]:
    """
    Optional LLM layer.

    The app works without LLM. When OPSLAB_USE_LLM=true, this function sends
    tool results to a local Ollama model and asks it to create a more natural
    decision-oriented report.
    """
    if not is_llm_enabled():
        return {
            "enabled": False,
            "used": False,
            "provider": "none",
            "model": None,
            "text": None,
            "error": None,
        }

    provider = os.getenv("OPSLAB_LLM_PROVIDER", "ollama").lower()

    if provider != "ollama":
        return {
            "enabled": True,
            "used": False,
            "provider": provider,
            "model": None,
            "text": None,
            "error": f"Nieobsługiwany provider LLM: {provider}",
        }

    model = os.getenv("OPSLAB_OLLAMA_MODEL", "llama3.2")
    url = os.getenv("OPSLAB_OLLAMA_URL", "http://localhost:11434/api/generate")

    system_prompt = """
Jesteś asystentem AI wspierającym analizę danych operacyjnych i automatyzację zadań IT.
Otrzymujesz wyniki narzędzi analitycznych w formie JSON.
Twoje zadanie:
- nie wymyślaj danych,
- bazuj wyłącznie na dostarczonych wynikach,
- napisz zwięzły raport po polsku,
- wskaż najważniejsze ryzyka,
- zaproponuj praktyczne działania,
- zachowaj profesjonalny, rzeczowy styl.
"""

    payload_prompt = f"""
Polecenie użytkownika:
{user_prompt}

Narzędzia użyte przez agenta:
{", ".join(tools_used)}

Wynik deterministyczny:
{deterministic_summary}

Surowe wyniki narzędzi JSON:
{json.dumps(raw_results, ensure_ascii=False, default=str, indent=2)}

Przygotuj końcową odpowiedź dla użytkownika.
"""

    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\n{payload_prompt}",
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))

        text = body.get("response", "").strip()

        if not text:
            return {
                "enabled": True,
                "used": False,
                "provider": "ollama",
                "model": model,
                "text": None,
                "error": "Model nie zwrócił treści odpowiedzi.",
            }

        return {
            "enabled": True,
            "used": True,
            "provider": "ollama",
            "model": model,
            "text": text,
            "error": None,
        }

    except urllib.error.URLError as exc:
        return {
            "enabled": True,
            "used": False,
            "provider": "ollama",
            "model": model,
            "text": None,
            "error": f"Nie można połączyć się z Ollama: {exc}",
        }
    except Exception as exc:
        return {
            "enabled": True,
            "used": False,
            "provider": "ollama",
            "model": model,
            "text": None,
            "error": str(exc),
        }