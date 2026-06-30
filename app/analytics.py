from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Device, Task, User

MIN_BIOS_VERSION = 1.13
SUPPORTED_OS = {"Windows 11 23H2", "Windows 11 24H2"}


def _bios_float(version: str) -> float:
    try:
        return float(version)
    except ValueError:
        return 0.0


def load_users_df(session: Session) -> pd.DataFrame:
    rows = session.execute(select(User)).scalars().all()
    return pd.DataFrame([
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "department": user.department,
            "role": user.role,
            "phone": user.phone,
            "is_active": user.is_active,
        }
        for user in rows
    ])


def load_devices_df(session: Session) -> pd.DataFrame:
    rows = session.execute(select(Device)).scalars().all()
    return pd.DataFrame([
        {
            "id": device.id,
            "hostname": device.hostname,
            "device_type": device.device_type,
            "os_version": device.os_version,
            "bios_version": device.bios_version,
            "last_seen": device.last_seen,
            "warranty_until": device.warranty_until,
            "owner_id": device.owner_id,
        }
        for device in rows
    ])


def load_tasks_df(session: Session) -> pd.DataFrame:
    rows = session.execute(select(Task)).scalars().all()
    today = date.today()
    data = []
    for task in rows:
        is_overdue = task.status != "Zakończone" and task.due_date < today
        delay_days = max((today - task.due_date).days, 0) if is_overdue else 0
        data.append(
            {
                "id": task.id,
                "title": task.title,
                "category": task.category,
                "team": task.team,
                "status": task.status,
                "priority": task.priority,
                "created_date": task.created_date,
                "due_date": task.due_date,
                "closed_date": task.closed_date,
                "estimated_hours": task.estimated_hours,
                "owner_id": task.owner_id,
                "is_overdue": is_overdue,
                "delay_days": delay_days,
            }
        )
    return pd.DataFrame(data)


def data_quality_summary(session: Session) -> dict[str, Any]:
    users = load_users_df(session)
    if users.empty:
        return {"total_users": 0, "issues_total": 0, "issues": []}

    missing_email = int(users["email"].isna().sum() + (users["email"].fillna("") == "").sum())
    missing_department = int(users["department"].isna().sum() + (users["department"].fillna("") == "").sum())
    missing_phone = int(users["phone"].isna().sum() + (users["phone"].fillna("") == "").sum())
    duplicate_email = int(users["email"].dropna().duplicated().sum())
    duplicate_phone = int(users["phone"].dropna().duplicated().sum())

    issues = [
        {"name": "Brak e-maila", "count": missing_email},
        {"name": "Brak działu", "count": missing_department},
        {"name": "Brak telefonu", "count": missing_phone},
        {"name": "Duplikaty e-mail", "count": duplicate_email},
        {"name": "Duplikaty telefonu", "count": duplicate_phone},
    ]
    return {
        "total_users": int(len(users)),
        "issues_total": int(sum(item["count"] for item in issues)),
        "issues": issues,
    }


def device_update_summary(session: Session) -> dict[str, Any]:
    devices = load_devices_df(session)
    today = date.today()
    if devices.empty:
        return {"total_devices": 0, "outdated_devices": 0, "inactive_devices": 0, "expired_warranty": 0}

    outdated_bios = devices["bios_version"].apply(_bios_float) < MIN_BIOS_VERSION
    unsupported_os = ~devices["os_version"].isin(SUPPORTED_OS)
    inactive = devices["last_seen"].apply(lambda x: (today - x).days > 45)
    warranty_expired = devices["warranty_until"].apply(lambda x: x < today)

    devices = devices.assign(
        outdated_bios=outdated_bios,
        unsupported_os=unsupported_os,
        inactive=inactive,
        warranty_expired=warranty_expired,
    )
    devices["needs_attention"] = outdated_bios | unsupported_os | inactive | warranty_expired

    return {
        "total_devices": int(len(devices)),
        "outdated_bios": int(outdated_bios.sum()),
        "unsupported_os": int(unsupported_os.sum()),
        "inactive_devices": int(inactive.sum()),
        "expired_warranty": int(warranty_expired.sum()),
        "needs_attention": int(devices["needs_attention"].sum()),
        "by_os": devices["os_version"].value_counts().to_dict(),
    }


def task_delay_summary(session: Session) -> dict[str, Any]:
    tasks = load_tasks_df(session)
    if tasks.empty:
        return {"total_tasks": 0, "overdue_tasks": 0, "avg_delay_days": 0.0}

    overdue = tasks[tasks["is_overdue"]]
    by_team = overdue.groupby("team").size().sort_values(ascending=False).to_dict() if not overdue.empty else {}
    by_category = overdue.groupby("category").size().sort_values(ascending=False).to_dict() if not overdue.empty else {}

    return {
        "total_tasks": int(len(tasks)),
        "overdue_tasks": int(len(overdue)),
        "avg_delay_days": round(float(overdue["delay_days"].mean()), 2) if not overdue.empty else 0.0,
        "max_delay_days": int(overdue["delay_days"].max()) if not overdue.empty else 0,
        "by_team": by_team,
        "by_category": by_category,
    }


def executive_summary(session: Session) -> dict[str, Any]:
    users_total = session.scalar(select(func.count(User.id))) or 0
    devices_total = session.scalar(select(func.count(Device.id))) or 0
    tasks_total = session.scalar(select(func.count(Task.id))) or 0
    quality = data_quality_summary(session)
    devices = device_update_summary(session)
    tasks = task_delay_summary(session)
    return {
        "users_total": int(users_total),
        "devices_total": int(devices_total),
        "tasks_total": int(tasks_total),
        "data_issues": quality["issues_total"],
        "devices_needing_attention": devices["needs_attention"],
        "overdue_tasks": tasks["overdue_tasks"],
    }
