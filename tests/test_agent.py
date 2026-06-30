from app.agent import DemoAgent
from app.database import get_engine, reset_db, session_scope
from app.demo_data import seed_demo_data


def test_agent_uses_tools_and_saves_report():
    engine = get_engine("sqlite:///:memory:")
    reset_db(engine)
    with session_scope(engine) as session:
        seed_demo_data(session, users_count=50, devices_count=30, tasks_count=70)
        response = DemoAgent().run(session, "Sprawdź urządzenia wymagające aktualizacji")

    assert "analyze_devices" in response.tools_used
    assert "find_outdated_devices" in response.tools_used
    assert response.summary
    assert "saved_report" in response.raw_results
