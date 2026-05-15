import asyncio, httpx, os

async def main():
    key = os.getenv("TAVILY_API_KEY", "")
    print(f"TAVILY_API_KEY present: {bool(key)}")
    payload = {
        "api_key": key,
        "query": "giá căn hộ Sunshine City Hà Nội",
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post("https://api.tavily.com/search", json=payload)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            print(f"Keys: {list(data.keys())}")
            print(f"Answer: {data.get('answer', 'N/A')}")
            print(f"Results count: {len(data.get('results', []))}")
            for r in data.get("results", [])[:2]:
                print(f"  - {r.get('title', '')}: {r.get('content', '')[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
