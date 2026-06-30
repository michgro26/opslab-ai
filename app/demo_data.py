from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_engine, reset_db, session_scope
from app.models import AutomationLog, Device, Task, User

FIRST_NAMES = [
    "Anna", "Jan", "Michał", "Katarzyna", "Piotr", "Agnieszka", "Tomasz", "Marta",
    "Paweł", "Magdalena", "Krzysztof", "Natalia", "Adam", "Monika", "Łukasz", "Karolina",
]
LAST_NAMES = [
    "Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamińska", "Lewandowski",
    "Zielińska", "Szymański", "Woźniak", "Dąbrowska", "Kozłowski", "Jankowski",
]
DEPARTMENTS = ["Finanse", "Operacje", "Analizy", "Kadry", "IT", "Obsługa", "Kontrola", "Administracja"]
ROLES = ["Specjalista", "Starszy specjalista", "Koordynator", "Analityk", "Administrator", "Konsultant"]
TEAMS = ["Zespół A", "Zespół B", "Zespół C", "Zespół D"]
TASK_CATEGORIES = ["Aktualizacja danych", "Weryfikacja", "Raportowanie", "Konfiguracja", "Kontrola jakości", "Migracja"]
TASK_STATUSES = ["Nowe", "W trakcie", "Oczekuje", "Zakończone"]
PRIORITIES = ["niski", "średni", "wysoki", "krytyczny"]
OS_VERSIONS = ["Windows 10 21H2", "Windows 10 22H2", "Windows 11 22H2", "Windows 11 23H2", "Windows 11 24H2"]
BIOS_VERSIONS = ["1.01", "1.04", "1.07", "1.10", "1.13", "1.16", "1.19", "1.22"]


def _random_name(index: int) -> tuple[str, str]:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return first, f"{last}-{index}" if index % 41 == 0 else last


def seed_users(session: Session, count: int) -> list[User]:
    users: list[User] = []
    used_emails: list[str] = []

    for i in range(1, count + 1):
        first, last = _random_name(i)
        full_name = f"{first} {last}"
        normalized = f"{first.lower()}.{last.lower().replace('ł', 'l').replace('ń', 'n').replace('ó', 'o')}"

        # Celowo wprowadzamy błędy jakości danych, żeby dashboard i agent miały co wykrywać.
        email = f"{normalized}@demo.local"
        if i % 17 == 0:
            email = None
        elif i % 53 == 0 and used_emails:
            email = random.choice(used_emails)
        else:
            used_emails.append(email)

        department = random.choice(DEPARTMENTS)
        if i % 19 == 0:
            department = None

        phone = f"+48 5{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"
        if i % 23 == 0:
            phone = None
        elif i % 61 == 0:
            phone = "+48 500 000 000"

        user = User(
            full_name=full_name,
            email=email,
            department=department,
            role=random.choice(ROLES),
            phone=phone,
            is_active=random.random() > 0.08,
        )
        users.append(user)
        session.add(user)

    session.flush()
    return users


def seed_devices(session: Session, users: Sequence[User], count: int) -> list[Device]:
    devices: list[Device] = []
    today = date.today()

    for i in range(1, count + 1):
        owner = random.choice(users) if random.random() > 0.07 else None
        device = Device(
            hostname=f"PC-{i:04d}",
            device_type=random.choice(["laptop", "desktop", "terminal", "mini-pc"]),
            os_name="Windows",
            os_version=random.choice(OS_VERSIONS),
            bios_version=random.choice(BIOS_VERSIONS),
            last_seen=today - timedelta(days=random.randint(0, 140)),
            warranty_until=today + timedelta(days=random.randint(-250, 900)),
            owner_id=owner.id if owner else None,
        )
        devices.append(device)
        session.add(device)

    session.flush()
    return devices


def seed_tasks(session: Session, users: Sequence[User], count: int) -> list[Task]:
    tasks: list[Task] = []
    today = date.today()

    for i in range(1, count + 1):
        created = today - timedelta(days=random.randint(0, 120))
        due = created + timedelta(days=random.randint(2, 30))
        status = random.choice(TASK_STATUSES)
        closed = None
        if status == "Zakończone":
            closed = due + timedelta(days=random.randint(-5, 18))

        task = Task(
            title=f"Zadanie operacyjne #{i:04d}",
            category=random.choice(TASK_CATEGORIES),
            team=random.choice(TEAMS),
            status=status,
            priority=random.choices(PRIORITIES, weights=[35, 45, 15, 5])[0],
            created_date=created,
            due_date=due,
            closed_date=closed,
            estimated_hours=round(random.uniform(0.5, 12), 1),
            owner_id=random.choice(users).id if users and random.random() > 0.05 else None,
        )
        tasks.append(task)
        session.add(task)

    session.add(
        AutomationLog(
            action_name="seed_demo_data",
            status="success",
            details="Utworzono syntetyczne dane demonstracyjne. Dane nie pochodzą z żadnego systemu zewnętrznego.",
        )
    )
    session.flush()
    return tasks


def seed_demo_data(session: Session, users_count: int = 250, devices_count: int = 180, tasks_count: int = 600) -> None:
    existing_users = session.scalar(select(func.count(User.id)))
    if existing_users:
        return

    users = seed_users(session, users_count)
    seed_devices(session, users, devices_count)
    seed_tasks(session, users, tasks_count)


def create_demo_database(reset: bool = False, users: int = 250, devices: int = 180, tasks: int = 600) -> None:
    engine = get_engine()
    if reset:
        reset_db(engine)
    else:
        from app.database import init_db
        init_db(engine)

    with session_scope(engine) as session:
        if reset:
            seed_demo_data(session, users, devices, tasks)
        else:
            seed_demo_data(session, users, devices, tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic data for OpsLab AI.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the SQLite database.")
    parser.add_argument("--users", type=int, default=250)
    parser.add_argument("--devices", type=int, default=180)
    parser.add_argument("--tasks", type=int, default=600)
    args = parser.parse_args()

    create_demo_database(reset=args.reset, users=args.users, devices=args.devices, tasks=args.tasks)
    print("Demo database ready: data/opslab_ai.db")


if __name__ == "__main__":
    main()
