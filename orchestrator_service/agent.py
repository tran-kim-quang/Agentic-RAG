import json
import httpx
from typing import TypedDict, List, Optional, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from shared.config import settings
from shared.schemas import RetrievedChunk, AgentResponse, UserInput
from orchestrator_service.guardrails import check_hallucination, sanitize_response
from orchestrator_service.sales_workflow import next_discovery_question, update_profile_from_intent


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    route: Literal["fast", "rag", "multimodal", "deep"]
    chunks: List[RetrievedChunk]
    answer: str
    follow_up: Optional[str]
    session_id: str
    lead_profile: dict


FAST_INTENTS = {"greeting", "smalltalk", "ack", "thanks", "bye"}
RAG_INTENTS = {"ask_project_info", "ask_price", "ask_policy", "ask_utility", "ask_inventory"}

SYSTEM_PROMPT = """Bạn là trợ lý AI sales bất động sản. Nhiệm vụ:
1. Trả lời khách hàng ngắn gọn, chính xác, thân thiện
2. Nếu cần thông tin dự án, dùng dữ liệu retrieve được
3. Luôn kết thúc bằng câu hỏi discovery hoặc soft CTA
4. Không bịa đặt thông tin không có trong context

Profile khách hiện tại:
{profile}

Context từ RAG:
{context}
"""


def _role_map(msg) -> str:
    t = getattr(msg, "type", "")
    if t == "human":
        return "user"
    if t == "ai":
        return "assistant"
    return t


async def _llm_generate(messages: list, model: str = None) -> str:
    model = model or settings.llm_model
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            f"{settings.ollama_llm_host}/api/chat",
            headers=settings.ollama_headers(),
            json={
                "model": model,
                "messages": [{"role": _role_map(m), "content": m.content} for m in messages],
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 8192},
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def classify_intent(state: AgentState) -> AgentState:
    last_msg = state["messages"][-1].content
    prompt = [
        SystemMessage(content="Phân loại ý định khách hàng thành: greeting, smalltalk, ask_project_info, ask_price, ask_policy, ask_utility, ask_inventory, discovery, booking, compare, other. Trả về JSON {\"intent\":\"...\"}"),
        HumanMessage(content=last_msg),
    ]
    raw = await _llm_generate(prompt, model=settings.llm_model)
    try: 
        parsed = json.loads(raw.strip().replace("```json", "").replace("```", "").strip())
        intent = parsed.get("intent", "other")
    except Exception:
        intent = "other"
    state["intent"] = intent
    if intent in FAST_INTENTS:
        state["route"] = "fast"
    elif intent in RAG_INTENTS:
        state["route"] = "rag"
    else:
        state["route"] = "deep"
    state["lead_profile"] = update_profile_from_intent(state.get("lead_profile", {}), intent, last_msg)
    return state


async def retrieve_context(state: AgentState) -> AgentState:
    if state["route"] == "fast":
        return state
    last_msg = state["messages"][-1].content
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.post(
            "http://localhost:8011/search",
            json={"query": last_msg, "top_k": settings.retrieval_top_k},
        )
        resp.raise_for_status()
        data = resp.json()
    state["chunks"] = [RetrievedChunk(**c) for c in data]
    return state


async def build_answer(state: AgentState) -> AgentState:
    if state["route"] == "fast":
        templates = {
            "greeting": "Dạ em chào anh/chị! Em là trợ lý AI tư vấn bất động sản. Hôm nay anh/chị đang tìm hiểu dự án nào ạ?",
            "smalltalk": "Dạ vâng ạ. Em rất vui được hỗ trợ anh/chị tìm hiểu bất động sản ạ.",
            "ack": "Dạ vâng, em hiểu rồi ạ.",
            "thanks": "Dạ không có gì ạ. Em rất vui được hỗ trợ anh/chị ạ.",
            "bye": "Dạ em chào anh/chị. Nếu cần tư vấn thêm, anh/chị cứ nhắn em ạ!",
        }
        state["answer"] = templates.get(state["intent"], "Dạ vâng ạ.")
        return state

    context = "\n\n".join(
        f"[{i+1}] {c.text} (nguồn: {c.source})"
        for i, c in enumerate(state["chunks"])
    )
    profile = json.dumps(state.get("lead_profile", {}), ensure_ascii=False, indent=2)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(profile=profile, context=context)),
        *state["messages"],
    ]
    state["answer"] = await _llm_generate(messages)
    return state


async def validate_answer(state: AgentState) -> AgentState:
    ok, reason = check_hallucination(state["answer"], state.get("chunks", []))
    if not ok:
        state["answer"] = f"Dạ em xin lỗi, em chưa có thông tin chính xác cho câu hỏi này. {reason}"
    state["answer"] = sanitize_response(state["answer"])
    return state


async def add_followup(state: AgentState) -> AgentState:
    if state["route"] == "fast":
        if state["intent"] == "greeting":
            state["follow_up"] = "Hôm nay anh/chị đang tìm hiểu dự án nào ạ?"
        return state
    state["follow_up"] = next_discovery_question(state.get("lead_profile", {}))
    return state


builder = StateGraph(AgentState)
builder.add_node("classify_intent", classify_intent)
builder.add_node("retrieve_context", retrieve_context)
builder.add_node("build_answer", build_answer)
builder.add_node("validate_answer", validate_answer)
builder.add_node("add_followup", add_followup)

builder.set_entry_point("classify_intent")
builder.add_edge("classify_intent", "retrieve_context")
builder.add_edge("retrieve_context", "build_answer")
builder.add_edge("build_answer", "validate_answer")
builder.add_edge("validate_answer", "add_followup")
builder.add_edge("add_followup", END)

agent_graph = builder.compile()


async def run_agent(user_input: UserInput, lead_profile: dict = None) -> AgentResponse:
    state = {
        "messages": [HumanMessage(content=user_input.text)],
        "intent": "",
        "route": "fast",
        "chunks": [],
        "answer": "",
        "follow_up": None,
        "session_id": user_input.session_id,
        "lead_profile": lead_profile or {},
    }
    result = await agent_graph.ainvoke(state)
    return AgentResponse(
        answer=result["answer"],
        intent=result["intent"],
        chunks=result.get("chunks", []),
        route=result["route"],
        follow_up=result.get("follow_up"),
    )
