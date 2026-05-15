import asyncio, httpx
async def t():
    async with httpx.AsyncClient() as c:
        r = await c.get("https://api.ollama.com/api/tags", headers={"Authorization":"Bearer 686ee00375b041d8be3043da747438f6.x4thTbqPE8pQn7QBwomKoJS5"})
        print(r.status_code)
asyncio.run(t())
