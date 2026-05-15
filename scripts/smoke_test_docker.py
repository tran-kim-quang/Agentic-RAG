"""Smoke test run inside Docker network."""
import sys, asyncio, json, time
sys.path.insert(0, "/app")
from orchestrator_service.agent import run_agent
from shared.schemas import UserInput

async def main():
    lines = []
    def out(s): lines.append(s); print(s, flush=True)

    out("=" * 60)
    out("AGENTIC RAG SALES ASSISTANT — SMOKE TEST (2 queries)")
    out("=" * 60)

    conversation = [
        {"role": "user", "text": "Xin chào, tôi đang tìm hiểu dự án Noble Palace Tây Hồ"},
        {"role": "user", "text": "Dự án này có căn hộ 2 phòng ngủ không, giá khoảng bao nhiêu?"},
    ]

    lead_profile = {}
    for turn in conversation:
        q = turn["text"]
        out(f"\n{'─' * 50}")
        out(f"[USER] {q}")
        t0 = time.time()
        resp = await run_agent(UserInput(text=q, session_id="smoke"), lead_profile=lead_profile)
        elapsed = time.time() - t0
        out(f"\n[AGENT] Intent={resp.intent} | Route={resp.route} | Time={elapsed:.1f}s")
        out(f"         Answer: {resp.answer[:350]}...")
        if resp.follow_up:
            out(f"         Follow-up: {resp.follow_up}")

    out(f"\n{'=' * 60}")
    out("FINAL EXTRACTED PROFILE")
    out(f"{'=' * 60}")
    out(json.dumps(lead_profile, ensure_ascii=False, indent=2))

    with open("/app/test_output.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    out("\n[Wrote results to /app/test_output.md]")

if __name__ == "__main__":
    asyncio.run(main())
