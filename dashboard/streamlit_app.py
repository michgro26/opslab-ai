from __future__ import annotations

from pathlib import Path
import sys
import os
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent import DemoAgent
from app.analytics import (
    data_quality_summary,
    device_update_summary,
    executive_summary,
    load_devices_df,
    load_tasks_df,
    load_users_df,
    task_delay_summary,
)
from app.database import get_engine, reset_db, session_scope
from app.demo_data import seed_demo_data
from app.models import AiReport, AutomationLog
from app.tools import calculate_operational_risk

def risk_color(score: float) -> str:
    if score >= 70:
        return "#ff4b4b"  # czerwony
    if score >= 40:
        return "#f5c542"  # żółty
    return "#2ecc71"      # zielony


def risk_badge(label: str, score: float) -> str:
    color = risk_color(score)
    return f"""
    <div style="
        padding: 14px 18px;
        border-radius: 12px;
        background: {color}22;
        border: 1px solid {color};
        color: {color};
        font-weight: 700;
        font-size: 18px;
        text-align: center;
    ">
        {label}
    </div>
    """


def risk_level_badge(level: str) -> str:
    normalized = level.lower()

    if normalized == "wysokie":
        color = "#ff4b4b"
    elif normalized == "średnie":
        color = "#f5c542"
    else:
        color = "#2ecc71"

    return f"""
    <span style="
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: {color}22;
        border: 1px solid {color};
        color: {color};
        font-weight: 700;
    ">
        {level.capitalize()}
    </span>
    """

st.set_page_config(page_title="OpsLab AI", page_icon="🤖", layout="wide")


def ensure_data(reset: bool = False) -> None:
    engine = get_engine()
    if reset:
        reset_db(engine)
    else:
        from app.database import init_db
        init_db(engine)
    with session_scope(engine) as session:
        seed_demo_data(session)


ensure_data()

st.title("OpsLab AI")
st.caption("Demonstracyjny agent AI do analizy danych operacyjnych i automatyzacji zadań IT na syntetycznych danych.")

with st.sidebar:
    st.header("Demo")
    st.write("Baza SQLite jest tworzona automatycznie w katalogu `data/`. Nie są potrzebne żadne zewnętrzne dostępy.")
    if st.button("Wygeneruj dane od nowa"):
        ensure_data(reset=True)
        st.success("Baza demo została odtworzona.")
        st.rerun()

    st.markdown("### Przykładowe polecenia")
    st.code("Znajdź problemy jakości danych użytkowników")
    st.code("Sprawdź urządzenia wymagające aktualizacji")
    st.code("Pokaż procesy po terminie i zaproponuj automatyzację")
    st.code("Uruchom automatyzację priorytetów dla zadań po terminie")
    st.code("Zrób audyt ryzyk operacyjnych i wskaż priorytety")

    st.markdown("### Tryb LLM")

    use_llm = st.toggle(
        "Użyj lokalnego LLM przez Ollama",
        value=os.getenv("OPSLAB_USE_LLM", "false").lower() in {"1", "true", "yes", "on"},
    )

    ollama_model = st.text_input(
        "Model Ollama",
        value=os.getenv("OPSLAB_OLLAMA_MODEL", "llama3.2"),
        help="Wpisz nazwę modelu dostępnego lokalnie w Ollama, np. llama3.2.",
    )

    os.environ["OPSLAB_USE_LLM"] = "true" if use_llm else "false"
    os.environ["OPSLAB_LLM_PROVIDER"] = "ollama"
    os.environ["OPSLAB_OLLAMA_MODEL"] = ollama_model.strip() or "llama3.2"

    if use_llm:
        st.info(
            "Tryb LLM jest włączony. Agent nadal wykonuje analizę narzędziami, "
            "ale końcowy raport zostanie wygenerowany przez lokalny model Ollama."
        )
    else:
        st.caption("Tryb LLM jest wyłączony. Aplikacja działa w pełni lokalnie bez modelu językowego.")

tab_dashboard, tab_agent, tab_risk, tab_data, tab_logs = st.tabs(
    ["Dashboard", "Agent AI", "Audyt ryzyka", "Dane", "Logi i raporty"]
)

with tab_dashboard:
    with session_scope() as session:
        summary = executive_summary(session)
        quality = data_quality_summary(session)
        devices = device_update_summary(session)
        tasks = task_delay_summary(session)
        risk = calculate_operational_risk(session)

    st.markdown("### Ocena ryzyka operacyjnego")

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.markdown(
            risk_badge(f"Risk score<br>{risk['score']}/100", risk["score"]),
            unsafe_allow_html=True,
        )

    with r2:
        st.markdown("**Poziom ryzyka**")
        st.markdown(
            risk_level_badge(risk["level"]),
            unsafe_allow_html=True,
        )

    with r3:
        st.metric("Opóźnione zadania", f"{risk['overdue_rate']}%")

    with r4:
        st.metric("Urządzenia do uwagi", f"{risk['device_risk_rate']}%")

    bar_color = risk_color(risk["score"])

    st.markdown(
        f"""
        <div style="
            width: 100%;
            background: #262730;
            border-radius: 999px;
            height: 18px;
            overflow: hidden;
            margin-top: 12px;
            margin-bottom: 24px;
        ">
            <div style="
                width: {risk['score']}%;
                background: {bar_color};
                height: 18px;
            "></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Użytkownicy", summary["users_total"])
    c2.metric("Urządzenia", summary["devices_total"])
    c3.metric("Zadania", summary["tasks_total"])
    c4.metric("Problemy danych", summary["data_issues"])
    c5.metric("Urządzenia do uwagi", summary["devices_needing_attention"])
    c6.metric("Zadania po terminie", summary["overdue_tasks"])

    left, right = st.columns(2)

    with left:
        st.subheader("Problemy jakości danych")
        issues_df = pd.DataFrame(quality["issues"])
        st.bar_chart(issues_df.set_index("name"))

    with right:
        st.subheader("Urządzenia według wersji OS")
        os_df = pd.DataFrame(devices["by_os"].items(), columns=["OS", "Liczba"])
        st.bar_chart(os_df.set_index("OS"))

    left, right = st.columns(2)

    with left:
        st.subheader("Zadania po terminie według zespołu")
        team_df = pd.DataFrame(tasks["by_team"].items(), columns=["Zespół", "Liczba"])
        if not team_df.empty:
            st.bar_chart(team_df.set_index("Zespół"))
        else:
            st.info("Brak zadań po terminie.")

    with right:
        st.subheader("Zadania po terminie według kategorii")
        category_df = pd.DataFrame(tasks["by_category"].items(), columns=["Kategoria", "Liczba"])
        if not category_df.empty:
            st.bar_chart(category_df.set_index("Kategoria"))
        else:
            st.info("Brak zadań po terminie.")

with tab_agent:
    st.subheader("Rozmowa z agentem demonstracyjnym")
    default_prompt = "Pokaż procesy po terminie i zaproponuj automatyzację"
    prompt = st.text_area("Polecenie", value=default_prompt, height=110)

    if st.button("Uruchom agenta", type="primary"):
        with session_scope() as session:
            response = DemoAgent().run(session, prompt)
        st.markdown("### Odpowiedź")
        st.write(response.summary)
        st.markdown("### Narzędzia użyte przez agenta")
        st.code("\n".join(response.tools_used))
        with st.expander("Surowe wyniki narzędzi"):
            st.json(response.raw_results)

with tab_risk:
    with session_scope() as session:
        risk = calculate_operational_risk(session)

    st.subheader("Audyt ryzyka operacyjnego")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            risk_badge(f"Risk score<br>{risk['score']}/100", risk["score"]),
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("**Poziom ryzyka**")
        st.markdown(
            risk_level_badge(risk["level"]),
            unsafe_allow_html=True,
        )

    with c3:
        st.metric("Problemy danych", f"{risk['data_quality_rate']}%")

    with c4:
        st.metric("Zadania po terminie", f"{risk['overdue_rate']}%")

    bar_color = risk_color(risk["score"])

    st.markdown(
        f"""
        <div style="
            width: 100%;
            background: #262730;
            border-radius: 999px;
            height: 18px;
            overflow: hidden;
            margin-top: 12px;
            margin-bottom: 24px;
        ">
            <div style="
                width: {risk['score']}%;
                background: {bar_color};
                height: 18px;
            "></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Najważniejsze obszary ryzyka")

    risk_areas_df = pd.DataFrame(risk["areas"])

    def color_risk_rows(row):
        value = row["wartosc"]

        if value >= 300:
            background = "background-color: rgba(255, 75, 75, 0.25)"
        elif value >= 100:
            background = "background-color: rgba(245, 197, 66, 0.25)"
        else:
            background = "background-color: rgba(46, 204, 113, 0.20)"

        return [background for _ in row]

    st.dataframe(
        risk_areas_df.style.apply(color_risk_rows, axis=1),
        use_container_width=True,
    )

    st.markdown("### Rekomendacje")
    for item in risk["recommendations"]:
        st.write(f"- {item}")

    report_md = "# OpsLab AI — audyt ryzyka operacyjnego\n\n"
    report_md += f"**Risk score:** {risk['score']}/100\n\n"
    report_md += f"**Poziom ryzyka:** {risk['level']}\n\n"

    report_md += "## Obszary ryzyka\n"
    for area in risk["areas"]:
        report_md += (
            f"- **{area['obszar']}** — {area['ryzyko']}: "
            f"{area['wartosc']} ({area['szczegoly']})\n"
        )

    report_md += "\n## Rekomendacje\n"
    for recommendation in risk["recommendations"]:
        report_md += f"- {recommendation}\n"

    st.download_button(
        "Pobierz raport Markdown",
        data=report_md,
        file_name="opslab-ai-risk-audit.md",
        mime="text/markdown",
    )

with tab_data:
    with session_scope() as session:
        users = load_users_df(session)
        devices_df = load_devices_df(session)
        tasks_df = load_tasks_df(session)

    data_tab1, data_tab2, data_tab3 = st.tabs(["Użytkownicy", "Urządzenia", "Zadania"])
    with data_tab1:
        st.dataframe(users.head(100), use_container_width=True)
    with data_tab2:
        st.dataframe(devices_df.head(100), use_container_width=True)
    with data_tab3:
        st.dataframe(tasks_df.head(100), use_container_width=True)

with tab_logs:
    with session_scope() as session:
        logs = session.query(AutomationLog).order_by(AutomationLog.created_at.desc()).limit(50).all()
        reports = session.query(AiReport).order_by(AiReport.created_at.desc()).limit(50).all()

        # Konwersja obiektów SQLAlchemy do słowników wewnątrz aktywnej sesji.
        # Dzięki temu Streamlit może bezpiecznie odświeżać widok po zamknięciu sesji.
        logs_rows = [
            {"czas": log.created_at, "akcja": log.action_name, "status": log.status, "szczegóły": log.details}
            for log in logs
        ]
        reports_rows = [
            {"czas": report.created_at, "polecenie": report.prompt, "narzędzia": report.tools_used, "podsumowanie": report.summary}
            for report in reports
        ]

    st.subheader("Logi automatyzacji")
    if logs_rows:
        logs_df = pd.DataFrame(logs_rows)
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("Brak logów automatyzacji. Uruchom agenta z poleceniem automatyzacji, aby utworzyć pierwszy log.")

    st.subheader("Raporty AI")
    if reports_rows:
        reports_df = pd.DataFrame(reports_rows)
        st.dataframe(reports_df, use_container_width=True)
    else:
        st.info("Brak raportów AI. Uruchom agenta, aby utworzyć pierwszy raport.")
