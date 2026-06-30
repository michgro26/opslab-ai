from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import DemoAgent
from app.analytics import executive_summary
from app.database import init_db, session_scope
from app.demo_data import seed_demo_data

app = FastAPI(title="OpsLab AI API", version="0.1.0")
agent = DemoAgent()


class AgentRequest(BaseModel):
    prompt: str


@app.on_event("startup")
def startup() -> None:
    engine = init_db()
    with session_scope(engine) as session:
        seed_demo_data(session)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/summary")
def summary() -> dict[str, Any]:
    with session_scope() as session:
        return executive_summary(session)


@app.post("/agent")
def run_agent(request: AgentRequest) -> dict[str, Any]:
    with session_scope() as session:
        response = agent.run(session, request.prompt)
        return {
            "prompt": response.prompt,
            "summary": response.summary,
            "tools_used": response.tools_used,
            "raw_results": response.raw_results,
        }
