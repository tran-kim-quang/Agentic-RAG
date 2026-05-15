import json
from typing import TypedDict, List, Optional, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from shared.config import settings
from shared.schemas import RetrievedChunk, AgentResponse, UserInput
from orchestrator_service.guardrails import check_hallucination, sanitize_response
from orchestrator_service.llm_client import llm_generate, llm_generate_dicts
from orchestrator_service.sales_workflow import (
    extract_profile_with_llm,
    assess_missing_info,
    generate_discovery_question_with_llm,
    build_rag_query,
)
from orchestrator_service.web_search import tavily_search


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    route: Literal["fast", "rag", "multimodal", "deep"]
    chunks: List[RetrievedChunk]
    answer: str
    follow_up: Optional[str]
    session_id: str
    lead_profile: dict
    sales_plan: dict
    turn_count: int


FAST_INTENTS = {"greeting", "smalltalk", "ack", "thanks", "bye"}
RAG_INTENTS = {"ask_project_info", "ask_price", "ask_policy", "ask_utility", "ask_inventory"}

SYSTEM_PROMPT = """Bạn là trợ lý AI sales bất động sản chuyên nghiệp.
Nhiệm vụ:
1. Trả lời khách hàng ngắn gọn, chính xác, thân thiện.
2. Dùng dữ liệu retrieve được để trả lời, không bịa đặt.
3. LUÔN kết thúc bằng câu hỏi discovery để thu thập thêm thông tin.
4. Hiểu rõ pain point của khách (vấn đề hiện tại) và interest (mong muốn).

Profile khách:
{profile}

Sales plan (thông tin còn thiếu):
{plan}

Context từ RAG + Web:
{context}
"""


# ------------------------------------------------------------------
# LangGraph nodes
# ------------------------------------------------------------------

async def classify_intent(state: AgentState):
    msg = state["messages"][-1]
    text = msg.content.lower()
    if any(w in text for w in FAST_INTENTS):
        return {"intent": "greeting", "route": "fast"}
    if any(w in text for w in {"giá", "bao nhiêu", "đắt", "rẻ", "chiết khấu"}):
        return {"intent": "ask_price", "route": "rag"}
    if any(w in text for w in {"chính sách", "vay", "ngân hàng", "trả góp", "lãi suất"}):
        return {"intent": "ask_policy", "route": "rag"}
    if any(w in text for w in {"căn hộ", "phòng ngủ", "pn", "loại", "diện tích", "còn hàng", "inventory"}):
        return {"intent": "ask_inventory", "route": "rag"}
    if any(w in text for w in {"dự án", "tiện ích", "vị trí", "chủ đầu tư"}):
        return {"intent": "ask_project_info", "route": "rag"}
    return {"intent": "ask_project_info", "route": "rag"}


async def extract_profile(state: AgentState):
    msg = state["messages"][-1]
    updated = await extract_profile_with_llm(
        llm_generate_dicts,
        msg.content,
        existing_profile=state.get("lead_profile", {}),
    )
    return {"lead_profile": updated}


async def assess_plan(state: AgentState):
    profile = state.get("lead_profile", {})
    plan = await assess_missing_info(llm_generate_dicts, profile)
    return {"sales_plan": plan}


async def retrieve_context(state: AgentState):
    profile = state.get("lead_profile", {})
    q = await build_rag_query(llm_generate_dicts, profile, state["messages"][-1].content)
    from retrieval_service.client import RetrievalClient
    client = RetrievalClient()
    chunks = await client.search(q, top_k=settings.retrieval_top_k)
    return {"chunks": chunks}


async def web_search(state: AgentState):
    chunks = state.get("chunks", [])
    # Fallback to web search if Qdrant returns too few results
    max_score = max((c.score for c in chunks), default=0.0)
    # NOTE: when using real semantic embedding (local Ollama), 0.65 is appropriate.
    # With pseudo-embedding fallback scores cluster around 0.77; raise to 0.80 if testing without real embed.
    if max_score >= 0.65:
        return {}

    q = state["messages"][-1].content if state["messages"] else ""
    web_chunks = await tavily_search(q, max_results=5)
    if web_chunks:
        chunks = chunks + web_chunks
    return {"chunks": chunks}


async def build_answer(state: AgentState):
    profile = state.get("lead_profile", {})
    chunks = state.get("chunks", [])
    context = "\n---\n".join([f"[{c.source}] {c.text}" for c in chunks[:5]])
    plan = state.get("sales_plan", {})
    plan_text = json.dumps(plan, ensure_ascii=False, indent=2)
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(profile=profile_text, plan=plan_text, context=context)),
        HumanMessage(content=state["messages"][-1].content),
    ]
    answer = await llm_generate(messages)
    answer = sanitize_response(answer)
    return {"answer": answer}


async def validate_answer(state: AgentState):
    ok, note = check_hallucination(state["answer"], state.get("chunks", []))
    if not ok:
        return {"answer": f"{state['answer']}\n\n[Lưu ý: {note}]"}
    return {}


async def generate_followup(state: AgentState):
    profile = state.get("lead_profile", {})
    plan = state.get("sales_plan", {})
    missing = plan.get("missing_fields", [])
    history = state["messages"][-1].content if state["messages"] else ""
    question = await generate_discovery_question_with_llm(llm_generate_dicts, profile, history, plan)
    return {"follow_up": question}


# ------------------------------------------------------------------
# Graph wiring
# ------------------------------------------------------------------

builder = StateGraph(AgentState)
builder.add_node("classify_intent", classify_intent)
builder.add_node("extract_profile", extract_profile)
builder.add_node("assess_plan", assess_plan)
builder.add_node("retrieve_context", retrieve_context)
builder.add_node("web_search", web_search)
builder.add_node("build_answer", build_answer)
builder.add_node("validate_answer", validate_answer)
builder.add_node("generate_followup", generate_followup)

builder.set_entry_point("classify_intent")
builder.add_edge("classify_intent", "extract_profile")
builder.add_edge("extract_profile", "assess_plan")
builder.add_edge("assess_plan", "retrieve_context")
builder.add_edge("retrieve_context", "web_search")
builder.add_edge("web_search", "build_answer")
builder.add_edge("build_answer", "validate_answer")
builder.add_edge("validate_answer", "generate_followup")
builder.add_edge("generate_followup", END)

agent_graph = builder.compile()


async def run_agent(user_input: UserInput, lead_profile: dict = None) -> AgentResponse:
    profile = lead_profile or {}
    state = {
        "messages": [HumanMessage(content=user_input.text)],
        "intent": "",
        "route": "fast",
        "chunks": [],
        "answer": "",
        "follow_up": None,
        "session_id": user_input.session_id,
        "lead_profile": profile,
        "sales_plan": {},
        "turn_count": 0,
    }
    result = await agent_graph.ainvoke(state)
    # Mutate caller's dict in place so multi-turn profile accumulates
    updated = result.get("lead_profile", {})
    profile.clear()
    profile.update(updated)
    return AgentResponse(
        answer=result["answer"],
        intent=result["intent"],
        chunks=result.get("chunks", []),
        route=result["route"],
        follow_up=result.get("follow_up"),
    )
