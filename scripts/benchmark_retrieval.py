"""Benchmark retrieval latency and quality."""
import sys, asyncio, time, statistics
sys.path.insert(0, "/home/meocon/work/sideprj")
from retrieval_service.client import RetrievalClient


QUERIES = [
    "giá căn 2 phòng ngủ",
    "chính sách thanh toán",
    "tiện ích dự án",
    "căn hộ view hồ bơi",
    "so sánh 1PN và 2PN",
]


async def main():
    client = RetrievalClient()
    latencies = []
    for q in QUERIES:
        t0 = time.perf_counter()
        results = await client.search(q, top_k=5)
        t1 = time.perf_counter()
        latencies.append(t1 - t0)
        print(f"Query: {q:30s} | Time: {(t1-t0)*1000:.1f}ms | Hits: {len(results)}")
    print(f"\nMean latency: {statistics.mean(latencies)*1000:.1f}ms")
    print(f"Max latency:  {max(latencies)*1000:.1f}ms")


if __name__ == "__main__":
    asyncio.run(main())
