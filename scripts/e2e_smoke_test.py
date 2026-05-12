"""End-to-end smoke test with sample data."""
import sys, asyncio
sys.path.insert(0, "/home/meocon/work/sideprj")
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
]


async def main():
    print("[1] Ingesting sample documents...")
    n = await ingest_documents(SAMPLE_DOCS)
    print(f"[1] Ingested {n} chunks\n")

    queries = [
        "Dự án này có tiện ích gì?",
        "Giá căn 2PN bao nhiêu?",
        "Xin chào",
    ]
    for q in queries:
        print(f"[2] Query: {q}")
        resp = await run_agent(UserInput(text=q, session_id="smoke"))
        print(f"   Intent: {resp.intent} | Route: {resp.route}")
        print(f"   Answer: {resp.answer[:200]}...")
        if resp.follow_up:
            print(f"   Follow-up: {resp.follow_up}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
