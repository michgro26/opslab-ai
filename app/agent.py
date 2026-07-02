from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.llm_client import generate_llm_report, is_llm_enabled
from app.tools import (
    analyze_data_quality,
    analyze_devices,
    analyze_task_delays,
    apply_priority_automation,
    calculate_operational_risk,
    create_automation_plan,
    find_outdated_devices,
    find_users_with_missing_data,
    save_ai_report,
)


@dataclass
class AgentResponse:
    prompt: str
    summary: str
    tools_used: list[str]
    raw_results: dict[str, Any]


def _format_data_quality(result: dict[str, Any]) -> str:
    issues = "\n".join(f"- {item['name']}: {item['count']}" for item in result.get("issues", []))
    return f"Wykryto {result.get('issues_total', 0)} problemów jakości danych.\n{issues}"


def _format_devices(result: dict[str, Any]) -> str:
    return (
        f"Wykryto {result.get('needs_attention', 0)} urządzeń wymagających uwagi. "
        f"Stary BIOS: {result.get('outdated_bios', 0)}, niewspierany OS: {result.get('unsupported_os', 0)}, "
        f"nieaktywne: {result.get('inactive_devices', 0)}, po gwarancji: {result.get('expired_warranty', 0)}."
    )


def _format_tasks(result: dict[str, Any]) -> str:
    by_team = result.get("by_team", {})
    leader = max(by_team, key=by_team.get) if by_team else "brak danych"
    return (
        f"Znaleziono {result.get('overdue_tasks', 0)} zadań po terminie. "
        f"Średnie opóźnienie: {result.get('avg_delay_days', 0)} dni. "
        f"Najwięcej opóźnień ma: {leader}."
    )


def _format_plan(result: dict[str, Any]) -> str:
    steps = "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(result.get("steps", [])))
    return f"{result.get('title', 'Plan automatyzacji')}\n{steps}\nEfekt: {result.get('estimated_impact')}"


def _format_risk(result: dict[str, Any]) -> str:
    areas = "\n".join(
        f"{idx + 1}. {item['obszar']}: {item['ryzyko']} — {item['wartosc']} ({item['szczegoly']})"
        for idx, item in enumerate(result.get("areas", []))
    )

    recommendations = "\n".join(
        f"{idx + 1}. {item}" for idx, item in enumerate(result.get("recommendations", []))
    )

    return (
        f"Ocena ryzyka operacyjnego: {result.get('score', 0)}/100, "
        f"poziom: {result.get('level', 'brak danych')}.\n\n"
        f"Najważniejsze obszary ryzyka:\n{areas}\n\n"
        f"Rekomendowane działania:\n{recommendations}"
    )


class DemoAgent:
    """Simple deterministic agent for portfolio/demo purposes.

    It works without external API access. It routes a natural-language prompt to
    predefined tools and writes a report to the local SQLite database.

    If OPSLAB_USE_LLM=true, it can additionally use a local Ollama model to
    rewrite the deterministic result into a more natural decision-oriented report.
    """

    def run(self, session: Session, prompt: str) -> AgentResponse:
        normalized = prompt.lower()
        tools_used: list[str] = []
        raw_results: dict[str, Any] = {}
        parts: list[str] = []

        wants_users = any(
            word in normalized
            for word in ["użytk", "email", "e-mail", "dział", "dane", "jakość"]
        )

        wants_devices = any(
            word in normalized
            for word in ["urząd", "bios", "system", "komputer", "aktualiz", "gwaranc"]
        )

        wants_tasks = any(
            word in normalized
            for word in ["zad", "termin", "opóź", "proces", "spraw"]
        )

        wants_automation = any(
            word in normalized
            for word in ["automatyz", "plan", "rekomend", "usprawn"]
        )

        wants_risk = any(
            phrase in normalized
            for phrase in [
                "ryzyk",
                "audyt",
                "kondycja",
                "kondycj",
                "przegląd",
                "obszary wymagające",
                "ocena operacyj",
                "największy problem",
                "największe problemy",
            ]
        )

        wants_apply = any(
            word in normalized
            for word in ["uruchom", "wykonaj", "zastosuj", "podnieś priorytet"]
        )

        if wants_risk:
            result = calculate_operational_risk(session)
            tools_used.append("calculate_operational_risk")
            raw_results["operational_risk"] = result
            parts.append(_format_risk(result))

        if wants_users:
            result = analyze_data_quality(session)
            tools_used.append("analyze_data_quality")
            raw_results["data_quality"] = result
            parts.append(_format_data_quality(result))

            sample = find_users_with_missing_data(session, limit=5)
            tools_used.append("find_users_with_missing_data")
            raw_results["users_with_missing_data"] = sample

        if wants_devices:
            result = analyze_devices(session)
            tools_used.append("analyze_devices")
            raw_results["devices"] = result
            parts.append(_format_devices(result))

            sample = find_outdated_devices(session, limit=5)
            tools_used.append("find_outdated_devices")
            raw_results["outdated_devices"] = sample

        if wants_tasks:
            result = analyze_task_delays(session)
            tools_used.append("analyze_task_delays")
            raw_results["task_delays"] = result
            parts.append(_format_tasks(result))

        if wants_automation:
            result = create_automation_plan(session)
            tools_used.append("create_automation_plan")
            raw_results["automation_plan"] = result
            parts.append(_format_plan(result))

        if wants_apply:
            result = apply_priority_automation(session)
            tools_used.append("apply_priority_automation")
            raw_results["applied_automation"] = result
            parts.append(f"Uruchomiono automatyzację. Zaktualizowano {result['updated_tasks']} rekordów.")

        if not tools_used:
            # Domyślny scenariusz demo: całościowy przegląd.
            for name, fn, formatter in [
                ("analyze_data_quality", analyze_data_quality, _format_data_quality),
                ("analyze_devices", analyze_devices, _format_devices),
                ("analyze_task_delays", analyze_task_delays, _format_tasks),
            ]:
                result = fn(session)
                tools_used.append(name)
                raw_results[name] = result
                parts.append(formatter(result))

        deterministic_summary = "\n\n".join(parts)

        llm_result = generate_llm_report(
            user_prompt=prompt,
            tools_used=tools_used,
            raw_results=raw_results,
            deterministic_summary=deterministic_summary,
        )

        raw_results["llm"] = {
            "enabled": llm_result.get("enabled", False),
            "used": llm_result.get("used", False),
            "provider": llm_result.get("provider"),
            "model": llm_result.get("model"),
            "error": llm_result.get("error"),
        }

        if llm_result.get("used"):
            summary = llm_result["text"]
        else:
            summary = deterministic_summary

            if is_llm_enabled():
                summary += (
                    "\n\nUwaga: tryb LLM był włączony, ale nie udało się użyć modelu. "
                    "Aplikacja zwróciła wynik z deterministycznego agenta."
                )

        report = save_ai_report(session, prompt, summary, tools_used)
        raw_results["saved_report"] = report

        return AgentResponse(
            prompt=prompt,
            summary=summary,
            tools_used=tools_used,
            raw_results=raw_results,
        )