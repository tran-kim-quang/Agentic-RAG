"""End-to-end smoke test — progressive sales qualification with RAG."""
import sys, asyncio, json, time
sys.path.insert(0, "/home/meocon/work/sideprj/Agentic-RAG")
from ingest_service.pipeline import ingest_documents
from orchestrator_service.agent import run_agent
from shared.schemas import UserInput

SAMPLE_DOCS = [
    {
        "source": "project_a_faq",
        "text": "Dự án Green Park có hồ bơi tràn bờ, phòng gym, khu vui chơi trẻ em. Căn 2PN diện tích 68m2 giá từ 3.2 tỷ. Chính sách thanh toán linh hoạt chia 6 đợt.",
        "metadata": {"project": "Green Park", "type": "faq"},
    },
    {
        "source": "project_a_price",
        "text": "Bảng giá Green Park: căn 1PN 45m2 giá 2.1 tỷ, 2PN 68m2 giá 3.2 tỷ, 3PN 95m2 giá 4.5 tỷ. Giá đã VAT, chưa phí bảo trì.",
        "metadata": {"project": "Green Park", "type": "price"},
    },
    {
        "source": "project_a_policy",
        "text": "Chính sách vay ngân hàng Green Park: hỗ trợ lãi suất 0% trong 12 tháng đầu, ân hạn gốc 24 tháng. Chiết khấu 5% nếu thanh toán sớm 95%.",
        "metadata": {"project": "Green Park", "type": "policy"},
    },
]


async def main():
    lines = []
    def out(s): lines.append(s); print(s, flush=True)

    out("=" * 60)
    out("AGENTIC RAG SALES ASSISTANT — SMOKE TEST")
    out("=" * 60)

    out("\n[1] Ingesting sample documents...")
    t0 = time.time()
    n = await ingest_documents(SAMPLE_DOCS)
    out(f"[1] Ingested {n} chunks in {time.time()-t0:.1f}s")

    # Multi-turn conversation to test progressive qualification
    conversation = [
        {"role": "user", "text": "Xin chào, tôi đang tìm hiểu dự án Green Park"},
        {"role": "user", "text": "Tôi cần căn 2PN, ngân sách khoảng 3.5 tỷ"},
        {"role": "user", "text": "Mua để ở, gia đình 3 người, con nhỏ 5 tuổi"},
        {"role": "user", "text": "Tôi đang thuê nhà chật chội, không có tiện ích cho con"},
        {"role": "user", "text": "Dự án này có chính sách vay ngân hàng không?"},
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
    out("FINAL EXTRACTED PROFILE (pain-points + interests)")
    out(f"{'=' * 60}")
    out(json.dumps(lead_profile, ensure_ascii=False, indent=2))

    with open("/home/meocon/work/sideprj/Agentic-RAG/test_output.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    out("\n[Wrote results to test_output.md]")


if __name__ == "__main__":
    asyncio.run(main())
