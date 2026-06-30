from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import (
    MIN_BIOS_VERSION,
    SUPPORTED_OS,
    data_quality_summary,
    device_update_summary,
    load_devices_df,
    load_tasks_df,
    load_users_df,
    task_delay_summary,
)
from app.models import AiReport, AutomationLog, Task, User


def find_users_with_missing_data(session: Session, limit: int = 20) -> dict[str, Any]:
    users = load_users_df(session)
    if users.empty:
        return {"count": 0, "rows": []}

    mask = (
        users["email"].isna()
        | users["department"].isna()
        | users["phone"].isna()
        | (users["email"].fillna("") == "")
        | (users["department"].fillna("") == "")
        | (users["phone"].fillna("") == "")
    )
    result = users[mask].head(limit)
    return {"count": int(mask.sum()), "rows": result.to_dict(orient="records")}


def find_outdated_devices(session: Session, limit: int = 20) -> dict[str, Any]:
    devices = load_devices_df(session)
    if devices.empty:
        return {"count": 0, "rows": []}

    outdated = devices[
        (devices["bios_version"].astype(float) < MIN_BIOS_VERSION)
        | (~devices["os_version"].isin(SUPPORTED_OS))
    ].copy()

    outdated["priority_score"] = 0
    outdated.loc[outdated["bios_version"].astype(float) < 1.07, "priority_score"] += 3
    outdated.loc[outdated["os_version"].str.contains("Windows 10"), "priority_score"] += 2
    outdated = outdated.sort_values("priority_score", ascending=False)

    return {"count": int(len(outdated)), "rows": outdated.head(limit).to_dict(orient="records")}


def analyze_task_delays(session: Session) -> dict[str, Any]:
    return task_delay_summary(session)


def analyze_data_quality(session: Session) -> dict[str, Any]:
    return data_quality_summary(session)


def analyze_devices(session: Session) -> dict[str, Any]:
    return device_update_summary(session)


def create_automation_plan(session: Session) -> dict[str, Any]:
    quality = data_quality_summary(session)
    devices = device_update_summary(session)
    tasks = task_delay_summary(session)
    plan: list[str] = []

    if quality["issues_total"] > 0:
        plan.append("Codziennie oznaczać aktywnych użytkowników z brakującym e-mailem, działem lub telefonem jako rekordy do poprawy.")
    if devices["needs_attention"] > 0:
        plan.append("Raz w tygodniu generować listę urządzeń z nieaktualnym systemem, starą wersją BIOS lub wygasłą gwarancją.")
    if tasks["overdue_tasks"] > 0:
        plan.append("Automatycznie podnosić priorytet zadań po terminie dłuższym niż 7 dni i raportować je do właściciela zespołu.")

    if not plan:
        plan.append("Nie wykryto krytycznych problemów. Utrzymać bieżący monitoring metryk operacyjnych.")

    return {
        "title": "Plan automatyzacji procesów operacyjnych",
        "steps": plan,
        "estimated_impact": "Redukcja ręcznej kontroli danych i szybsze wskazywanie rekordów wymagających reakcji.",
    }


def apply_priority_automation(session: Session) -> dict[str, Any]:
    tasks = session.execute(select(Task).where(Task.status != "Zakończone")).scalars().all()
    updated = 0
    today = datetime.utcnow().date()
    for task in tasks:
        delay_days = (today - task.due_date).days
        if delay_days > 14 and task.priority in {"niski", "średni"}:
            task.priority = "wysoki"
            updated += 1
        elif delay_days > 30 and task.priority != "krytyczny":
            task.priority = "krytyczny"
            updated += 1

    log = AutomationLog(
        action_name="auto_prioritize_overdue_tasks",
        status="success",
        details=f"Zaktualizowano priorytet dla {updated} zadań po terminie.",
    )
    session.add(log)
    session.flush()
    return {"updated_tasks": updated, "log_id": log.id}

def calculate_operational_risk(session: Session) -> dict[str, Any]:
    quality = data_quality_summary(session)
    devices = device_update_summary(session)
    tasks = task_delay_summary(session)

    total_users = max(int(quality.get("total_users", 0)), 1)
    total_devices = max(int(devices.get("total_devices", 0)), 1)
    total_tasks = max(int(tasks.get("total_tasks", 0)), 1)

    data_quality_rate = min(quality.get("issues_total", 0) / total_users, 1)
    device_risk_rate = min(devices.get("needs_attention", 0) / total_devices, 1)
    overdue_rate = min(tasks.get("overdue_tasks", 0) / total_tasks, 1)
    delay_risk_rate = min(tasks.get("avg_delay_days", 0) / 60, 1)

    score = round(
        data_quality_rate * 25
        + device_risk_rate * 30
        + overdue_rate * 35
        + delay_risk_rate * 10,
        1,
    )

    if score >= 70:
        level = "wysokie"
    elif score >= 40:
        level = "średnie"
    else:
        level = "niskie"

    by_team = tasks.get("by_team", {})
    by_category = tasks.get("by_category", {})
    top_team = max(by_team, key=by_team.get) if by_team else "brak danych"
    top_category = max(by_category, key=by_category.get) if by_category else "brak danych"

    areas = [
        {
            "obszar": "Procesy",
            "ryzyko": "Zadania po terminie",
            "wartosc": tasks.get("overdue_tasks", 0),
            "szczegoly": f"Najwięcej opóźnień: {top_team}; kategoria: {top_category}",
        },
        {
            "obszar": "Urządzenia",
            "ryzyko": "Urządzenia wymagające uwagi",
            "wartosc": devices.get("needs_attention", 0),
            "szczegoly": f"BIOS: {devices.get('outdated_bios', 0)}, OS: {devices.get('unsupported_os', 0)}, gwarancja: {devices.get('expired_warranty', 0)}",
        },
        {
            "obszar": "Jakość danych",
            "ryzyko": "Braki i duplikaty danych użytkowników",
            "wartosc": quality.get("issues_total", 0),
            "szczegoly": "Weryfikacja e-maili, działów, telefonów i duplikatów",
        },
    ]

    areas = sorted(areas, key=lambda item: item["wartosc"], reverse=True)

    recommendations: list[str] = []

    if tasks.get("overdue_tasks", 0) > 0:
        recommendations.append(
            "Ustawić automatyczne podnoszenie priorytetu dla zadań opóźnionych powyżej 14 dni."
        )

    if devices.get("needs_attention", 0) > 0:
        recommendations.append(
            "Generować tygodniową listę urządzeń z przestarzałym BIOS, niewspieranym OS lub wygasłą gwarancją."
        )

    if quality.get("issues_total", 0) > 0:
        recommendations.append(
            "Uruchomić cykliczną kontrolę jakości danych użytkowników i oznaczać rekordy wymagające poprawy."
        )

    if not recommendations:
        recommendations.append("Nie wykryto wysokich ryzyk. Utrzymać monitoring metryk operacyjnych.")

    return {
        "score": score,
        "level": level,
        "data_quality_rate": round(data_quality_rate * 100, 1),
        "device_risk_rate": round(device_risk_rate * 100, 1),
        "overdue_rate": round(overdue_rate * 100, 1),
        "avg_delay_days": tasks.get("avg_delay_days", 0),
        "areas": areas,
        "recommendations": recommendations,
    }

def save_ai_report(session: Session, prompt: str, summary: str, tools_used: list[str]) -> dict[str, Any]:
    report = AiReport(prompt=prompt, summary=summary, tools_used=", ".join(tools_used))
    session.add(report)
    session.flush()
    return {"report_id": report.id}


TOOL_REGISTRY = {
    "find_users_with_missing_data": find_users_with_missing_data,
    "find_outdated_devices": find_outdated_devices,
    "analyze_task_delays": analyze_task_delays,
    "analyze_data_quality": analyze_data_quality,
    "analyze_devices": analyze_devices,
    "create_automation_plan": create_automation_plan,
    "apply_priority_automation": apply_priority_automation,
    "calculate_operational_risk": calculate_operational_risk,
}
