"""Test web-search fallback with an out-of-db query."""
import sys, asyncio
sys.path.insert(0, "/app")
from orchestrator_service.agent import run_agent
from shared.schemas import UserInput

async def main():
    lead_profile = {}
    # Query about a project NOT in the database to force web fallback
    q = "Dự án Vinhomes Ocean Park có gì nổi bật, giá bao nhiêu?"
    print(f"[USER] {q}")
    resp = await run_agent(UserInput(text=q, session_id="webtest"), lead_profile=lead_profile)
    print(f"\n[AGENT] Intent={resp.intent} | Route={resp.route}")
    print(f"         Answer: {resp.answer[:500]}...")
    if resp.follow_up:
        print(f"         Follow-up: {resp.follow_up}")
    print(f"\nSources in chunks:")
    for c in resp.chunks:
        print(f"  - {c.source} (score={c.score:.2f})")

asyncio.run(main())
