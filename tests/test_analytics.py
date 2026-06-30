from app.analytics import data_quality_summary, device_update_summary, task_delay_summary
from app.database import get_engine, reset_db, session_scope
from app.demo_data import seed_demo_data


def make_session():
    engine = get_engine("sqlite:///:memory:")
    reset_db(engine)
    return engine


def test_analytics_returns_expected_keys():
    engine = make_session()
    with session_scope(engine) as session:
        seed_demo_data(session, users_count=60, devices_count=40, tasks_count=80)
        quality = data_quality_summary(session)
        devices = device_update_summary(session)
        tasks = task_delay_summary(session)

    assert quality["total_users"] == 60
    assert "issues_total" in quality
    assert devices["total_devices"] == 40
    assert "needs_attention" in devices
    assert tasks["total_tasks"] == 80
    assert "overdue_tasks" in tasks
