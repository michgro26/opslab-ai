from app.database import get_engine, reset_db, session_scope
from app.demo_data import seed_demo_data
from app.tools import apply_priority_automation, create_automation_plan, find_users_with_missing_data


def test_tools_work_on_synthetic_data():
    engine = get_engine("sqlite:///:memory:")
    reset_db(engine)
    with session_scope(engine) as session:
        seed_demo_data(session, users_count=80, devices_count=50, tasks_count=120)
        missing = find_users_with_missing_data(session)
        plan = create_automation_plan(session)
        automation = apply_priority_automation(session)

    assert "count" in missing
    assert plan["steps"]
    assert "updated_tasks" in automation
