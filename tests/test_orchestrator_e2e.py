import sys
sys.path.insert(0, "/home/meocon/work/sideprj")
import pytest
from orchestrator_service.agent import run_agent
from shared.schemas import UserInput


@pytest.mark.asyncio
async def test_fast_path_greeting():
    response = await run_agent(UserInput(text="Xin chào", session_id="test1"))
    assert response.route == "fast"
    assert "chào" in response.answer.lower()


@pytest.mark.asyncio
async def test_rag_path_project_question():
    response = await run_agent(UserInput(text="Dự án này có tiện ích gì?", session_id="test2"))
    assert response.route in {"rag", "deep"}
